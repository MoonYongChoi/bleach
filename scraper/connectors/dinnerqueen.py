"""디너의여왕(Dinnerqueen) 커넥터.

구조 메모 (2026-10-29 probe.py 조사):
- 목록 1페이지: GET https://dinnerqueen.net/taste?ct=전체 — 서버 렌더링, 카드 30개.
- 다음 페이지: 무한스크롤이 POST /taste/taste_list?...&page=N 으로 같은 마크업의 카드 조각을 받는다.
  requests로 같은 요청을 보내면 첫 페이지가 다시 와서, 브라우저로 스크롤해 불러온다.
- 카드: <div class="qz-dq-card campaign">
    <a class="qz-dq-card__link" href="/taste/1617679" title="[프리미엄][릴스][에이지투웨니스] 시그니처 에센스팩트 기획세트 신청하기">
      <img alt="..." src="https://dq-files.gcdn.ntruss.com/posts/....webp">
      <div class="qz-dq-card__badge-row"> ... <strong>릴스</strong> ... </div>          ← 릴스/클립 뱃지
    </a>
    <div class="qz-dq-card__text"> <p>[프리미엄][릴스][브랜드] 제목</p> <p>제공내역</p> ... 오늘까지 | 신청 218 / 30 </div>
- 제목 괄호에 [지역]이 있으면 방문형, 없으면 제품 제공형으로 본다 (카드에 유형 표시가 따로 없음 — 실제 페이지로 재확인 필요).
- robots.txt는 전체 Disallow — 사용자 결정(2026-10-29)으로 수집하되 요청 간격을 둔다.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from connectors.base import Connector, RawCampaign, split_title_brackets

BASE_URL = "https://dinnerqueen.net"
LIST_URL = f"{BASE_URL}/taste"
HEADERS = {"User-Agent": "Mozilla/5.0 (BleachBot/1.0; +https://bleach.app)"}

DAYS_LEFT_RE = re.compile(r"(\d+)\s*일\s*(?:남음|남았)")
DDAY_RE = re.compile(r"D\s*-\s*(\d+)", re.I)
RECRUIT_RE = re.compile(r"신청\s*([\d,]+)\s*/\s*([\d,]+)")
_CHANNEL_BADGES = {"릴스", "클립", "쇼츠", "숏츠", "블로그", "인스타", "인스타그램", "유튜브", "틱톡"}
_NOT_DESCRIPTION = re.compile(r"신청|남음|오늘까지|내일까지|포인트|Only|^\[")


def parse_cards(html: str) -> list[RawCampaign]:
    soup = BeautifulSoup(html, "html.parser")
    campaigns: list[RawCampaign] = []
    for card in soup.select("div.qz-dq-card.campaign"):
        link = card.select_one("a.qz-dq-card__link[href]")
        if not link:
            continue
        m = re.search(r"/taste/(\d+)", link["href"])
        if not m:
            continue

        raw_title = (link.get("title") or "").removesuffix("신청하기").strip()
        img = link.select_one("img")
        if not raw_title and img:
            raw_title = img.get("alt", "")
        title, brackets = split_title_brackets(raw_title)

        text = card.get_text(" ", strip=True)
        if "오늘까지" in text:
            days_left = 0
        elif "내일까지" in text:
            days_left = 1
        else:
            dm = DAYS_LEFT_RE.search(text) or DDAY_RE.search(text)
            days_left = int(dm.group(1)) if dm else None
        rm = RECRUIT_RE.search(text)

        paragraphs = [p.get_text(" ", strip=True) for p in card.select(".qz-dq-card__text p")]
        description = next((p for p in paragraphs[1:] if p and not _NOT_DESCRIPTION.search(p)), None)

        # 뱃지 줄에는 채널(릴스/클립)뿐 아니라 "포인트", "랜덤픽" 같은 것도 있다 — 채널 단어만 남긴다
        badges = [
            t
            for t in (b.get_text(strip=True) for b in card.select(".qz-dq-card__badge-row strong"))
            if t in _CHANNEL_BADGES
        ]
        region = (brackets["regions"] or [None])[0]

        campaigns.append(
            RawCampaign(
                source_url=f"{BASE_URL}/taste/{m.group(1)}",
                title=title,
                description=description,
                vendor=(brackets["others"] or [None])[0],
                image_url=urljoin(BASE_URL, img["src"]) if img and img.get("src") else None,
                region_raw=region,
                deadline_days_left=days_left,
                applicant_count=rm.group(1) if rm else None,
                recruit_count=rm.group(2) if rm else None,
                type_hint="방문" if region else "배송",
                channels_raw=badges + brackets["channels"],
            )
        )
    return campaigns


class DinnerqueenConnector(Connector):
    key = "dinnerqueen"
    label = "디너의여왕"
    base_url = BASE_URL
    # 다음 페이지 POST를 requests로 흉내 내면 첫 페이지가 그대로 다시 온다 (2026-10-29 시험 실행) —
    # 사이트가 실제로 하는 대로 브라우저에서 스크롤해서 불러온다.
    needs_browser = True
    # 뱃지에 릴스/클립만 따로 표시되고 나머지는 블로그 체험단이다
    default_channels = ("blog",)

    def __init__(self, scrolls: int = 8):
        self.scrolls = scrolls

    def fetch(self) -> list[RawCampaign]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(f"{LIST_URL}?ct=전체", wait_until="networkidle", timeout=45000)
            page.wait_for_selector("div.qz-dq-card.campaign", timeout=20000)
            for i in range(self.scrolls):
                before = page.locator("div.qz-dq-card.campaign").count()
                page.mouse.wheel(0, 8000)
                page.wait_for_timeout(2000)
                after = page.locator("div.qz-dq-card.campaign").count()
                print(f"[디너의여왕] 스크롤 {i + 1}: 카드 {before} → {after}")
                if after == before:
                    break
            html = page.content()
            browser.close()

        campaigns: list[RawCampaign] = []
        seen: set[str] = set()
        for c in parse_cards(html):
            if c.source_url not in seen:
                seen.add(c.source_url)
                campaigns.append(c)
        from collections import Counter

        badge_counts = Counter(b for c in campaigns for b in set(c.channels_raw))
        print(f"[디너의여왕] 뱃지/제목 괄호 값 집계: {dict(badge_counts)} (전체 {len(campaigns)}건)")
        no_badge = [c for c in campaigns if not c.channels_raw]
        print(f"[디너의여왕] 채널 표시가 없는 카드 {len(no_badge)}건")
        for c in campaigns[:3] + campaigns[-3:]:
            print(f"[디너의여왕] 표본 {c.source_url} 제목={c.title!r} 채널원본={c.channels_raw}")
        return campaigns

if __name__ == "__main__":
    items = DinnerqueenConnector(scrolls=2).fetch()
    print(f"수집된 캠페인: {len(items)}개")
    for c in items[:5]:
        print(c)
