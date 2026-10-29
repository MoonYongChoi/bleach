"""모두블로그(Modublog) 커넥터.

구조 메모 (2026-10-29 probe.py 조사):
- https://www.modublog.co.kr/product 는 봇 확인 페이지(자바스크립트로 CUPID 쿠키를 만든 뒤 다시 이동)가
  먼저 떠서 requests로는 빈 페이지만 온다 → Playwright로 연다. 로그인은 필요 없다.
- 목록은 무한스크롤 (POST /product_skin_ajax/ajax_list.php) — 스크롤해서 불러온 뒤 한 번에 읽는다.
- 카드: <div class="c_box">
    <div class="imgArea"><a href=".../product/49263"><img alt="[서울/둔촌동역] 에이유주얼리 1기"
         src=".../data/list_thumb/fashion/thumb_49263_247742.jpg"></a></div>       ← 경로의 fashion = 분류
    <p class="icon_area"><span class="btn_ca blog_color">블로그</span></p>         ← 리뷰 채널
    <p class="c_title"><a>[서울/둔촌동역] 에이유주얼리 1기</a></p>                   ← [지역] 제목
    <p class="pr_subject_sub">실버 목걸이</p>                                       ← 제공내역
    <span class="recruit">신청 <strong>1</strong><em>/</em>7</span>
    <span class="deadline"><strong>13</strong>일 남음</span>
- robots.txt도 봇 확인 페이지 뒤에 있어 확인 못 함.
"""

from __future__ import annotations

import re

from connectors.base import Connector, RawCampaign, split_title_brackets

BASE_URL = "https://www.modublog.co.kr"
LIST_URL = f"{BASE_URL}/product"

RECRUIT_RE = re.compile(r"신청\s*([\d,]+)\s*/\s*([\d,]+)")
DAYS_LEFT_RE = re.compile(r"(\d+)\s*일\s*남음|D\s*-\s*(\d+)", re.I)
TODAY_WORDS = ("오늘", "D-day", "D-DAY", "마감임박", "금일")
# "바로체험"은 마감 없이 선정 즉시 진행하는 캠페인 — 마감일 없음(상시모집)으로 둔다
THUMB_CATEGORY_RE = re.compile(r"/list_thumb/([a-z_]+)/")

CARD_JS = """els => els.map(el => ({
    href: el.querySelector('a[href*="/product/"]')?.href || null,
    title: el.querySelector('.c_title')?.innerText?.trim() || null,
    offer: el.querySelector('.pr_subject_sub')?.innerText?.trim() || null,
    image: el.querySelector('.imgArea img')?.getAttribute('src') || null,
    channels: [...el.querySelectorAll('.icon_area span')].map(s => s.innerText.trim()).filter(Boolean),
    recruit: el.querySelector('.recruit')?.innerText || '',
    deadline: el.querySelector('.deadline')?.innerText || ''
}))"""


def to_raw(card: dict) -> RawCampaign | None:
    m = re.search(r"/product/(\d+)", card.get("href") or "")
    if not m or not card.get("title"):
        return None
    title, brackets = split_title_brackets(card["title"])
    rm = RECRUIT_RE.search(card.get("recruit") or "")
    deadline_text = card.get("deadline") or ""
    dm = DAYS_LEFT_RE.search(deadline_text)
    if dm:
        days_left = int(dm.group(1) or dm.group(2))
    elif "내일" in deadline_text:
        days_left = 1
    elif any(w in deadline_text for w in TODAY_WORDS):
        days_left = 0
    else:
        days_left = None
    cm = THUMB_CATEGORY_RE.search(card.get("image") or "")
    region = (brackets["regions"] or [None])[0]
    return RawCampaign(
        source_url=f"{BASE_URL}/product/{m.group(1)}",
        title=title,
        description=card.get("offer"),
        vendor=(brackets["others"] or [None])[0],
        image_url=card.get("image"),
        region_raw=region,
        deadline_days_left=days_left,
        applicant_count=rm.group(1) if rm else None,
        recruit_count=rm.group(2) if rm else None,
        category_raw=cm.group(1) if cm else None,
        type_hint=(brackets["types"] or [None])[0] or ("방문" if region else "배송"),
        channels_raw=card.get("channels", []) + brackets["channels"],
    )


class ModublogConnector(Connector):
    key = "modublog"
    label = "모두블로그"
    base_url = BASE_URL
    needs_browser = True

    def __init__(self, scrolls: int = 12):
        self.scrolls = scrolls

    def prepare_browser(self, context) -> None:
        # 봇 확인 쿠키를 먼저 받아둔다
        page = context.new_page()
        page.goto(BASE_URL, wait_until="networkidle", timeout=45000)
        page.close()

    def fetch(self) -> list[RawCampaign]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            self.prepare_browser(context)
            page = context.new_page()
            page.goto(LIST_URL, wait_until="networkidle", timeout=45000)
            page.wait_for_selector("div.c_box", timeout=20000)
            for _ in range(self.scrolls):
                before = page.locator("div.c_box").count()
                page.mouse.wheel(0, 6000)
                page.wait_for_timeout(1500)  # 무한스크롤 요청 간격 겸 사이트 부담 줄이기
                if page.locator("div.c_box").count() == before:
                    break
            cards = page.eval_on_selector_all("div.c_box", CARD_JS)
            browser.close()

        unparsed = [
            c.get("deadline", "").strip()
            for c in cards
            if c.get("deadline")
            and not DAYS_LEFT_RE.search(c["deadline"])
            and not any(w in c["deadline"] for w in (*TODAY_WORDS, "내일", "바로체험"))
        ]
        if unparsed:
            print(f"[모두블로그] 마감 표기를 못 읽은 카드 {len(unparsed)}개, 예: {sorted(set(unparsed))[:8]}")
        no_deadline = sum(1 for c in cards if not (c.get("deadline") or "").strip())
        if no_deadline:
            print(f"[모두블로그] 마감 표시가 아예 없는 카드 {no_deadline}개 (상시모집일 수 있음)")

        campaigns: list[RawCampaign] = []
        seen: set[str] = set()
        for card in cards:
            raw = to_raw(card)
            if raw and raw.source_url not in seen:
                seen.add(raw.source_url)
                campaigns.append(raw)
        if not campaigns:
            raise RuntimeError("모두블로그 목록에서 카드를 하나도 읽지 못했습니다 (봇 확인 통과 실패 가능)")
        return campaigns


if __name__ == "__main__":
    items = ModublogConnector(scrolls=2).fetch()
    print(f"수집된 캠페인: {len(items)}개")
    for c in items[:5]:
        print(c)
