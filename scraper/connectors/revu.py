"""레뷰(Revu) 커넥터.

레뷰는 AngularJS SPA라 서버 렌더링 HTML에 데이터가 없고, 카테고리 전체 목록은
로그인한 사용자에게만 열린다 (비로그인 시 /login으로 리다이렉트됨).
그래서 이 스크래퍼만 Playwright로 실제 로그인 후 렌더링된 DOM을 읽는다.

환경변수 REVU_ID / REVU_PW 필요 (.env.local).

구조 메모 (2026-10-28 재조사):
- 로그인: POST 없이 /login 페이지의 input[name=email], input[name=password] +
  "로그인" 버튼 클릭으로 처리 (reCAPTCHA는 이번 조사에서는 나타나지 않았음).
- 목록: /category/제품, /category/지역 (로그인 필요). 카드 구조:
    <a href="/campaign/ID">
      <img class="thumb-img" src="...">
      <p class="card-title">[괄호 프리픽스] 제목</p>
      <p class="card-desc">제공내역</p>
      <strong class="card-status">N일 남음 | 마감 임박 | 모집마감 | ...</strong>
      "신청 123 / 10명"  (고유 클래스 없이 텍스트로만 존재 — innerText로 추출)
    </a>
  "[괄호 프리픽스]"는 카테고리에 따라 의미가 다르다 — /category/지역은 지역명,
  /category/제품은 업체/브랜드명이다.
- 정확한 마감 "일수"만 주어지고 날짜는 구조화되어 있지 않음.
"""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from typing import Optional
from urllib.parse import urljoin

from connectors.base import Connector, RawCampaign
from normalize import today_kst

BASE_URL = "https://www.revu.net"
CATEGORIES = ["제품", "지역"]

BRACKET_PREFIX_RE = re.compile(r"^\[([^\]]+)\]\s*")
DAYS_LEFT_RE = re.compile(r"(\d+)\s*일\s*남음")
APPLICANT_RE = re.compile(r"신청\s*([\d,]+)\s*/\s*(\d+)\s*명")


def _login(context) -> bool:
    """로그인 후 /login 이 아닌 페이지로 넘어갔는지로 판정한다.

    예전엔 "페이지에 로그인 링크가 없으면 성공"으로 봤는데, 로그인 페이지 자체에도 그 링크가 없어서
    로그인이 실패해도 성공으로 판정됐다 (2026-10-29 레뷰 0건 수집의 원인).
    """
    email = os.environ.get("REVU_ID")
    pw = os.environ.get("REVU_PW")
    if not email or not pw:
        raise RuntimeError("REVU_ID / REVU_PW 환경변수가 설정되어 있지 않습니다.")

    page = context.new_page()
    page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=30000)
    page.fill("input[name=email]", email)
    page.fill("input[name=password]", pw)
    page.click('button:has-text("로그인")')
    try:
        page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
        page.close()
        return True
    except Exception:  # noqa: BLE001 - 시간 초과 = 로그인 실패, 이유를 모아서 알린다
        body = page.inner_text("body")
        has_captcha = page.locator('iframe[src*="recaptcha"], iframe[title*="reCAPTCHA"]').count() > 0
        hint = next(
            (line.strip() for line in body.splitlines()
             if any(k in line for k in ("비밀번호", "아이디", "이메일", "일치", "잠금", "제한", "인증"))),
            "",
        )
        page.close()
        raise RuntimeError(
            "레뷰 로그인 실패"
            + (" — reCAPTCHA가 떴습니다 (반복 로그인으로 차단됐을 수 있음)" if has_captcha else "")
            + (f" — 사이트 메시지: {hint[:80]}" if hint else "")
        )


CLOSED_MARKERS = ("모집마감", "마감완료", "모집완료", "발표완료")


def _is_closed(status_text: str) -> bool:
    return any(marker in status_text for marker in CLOSED_MARKERS)


def _parse_deadline(status_text: str) -> Optional[date]:
    status_text = status_text.strip()
    today = today_kst()  # Actions는 UTC라 03:30 KST 실행분에서 하루 밀리지 않게
    m = DAYS_LEFT_RE.search(status_text)
    if m:
        return today + timedelta(days=int(m.group(1)))
    if "마감" in status_text:  # "마감 임박" 등 정확한 일수 없음 → 오늘로 간주
        return today
    return None


class RevuConnector(Connector):
    key = "revu"
    label = "레뷰"
    base_url = BASE_URL
    needs_browser = True
    required_env = ("REVU_ID", "REVU_PW")
    # /category/{제품,지역} 페이지 이름이 곧 유형이다.
    type_hints = {"제품": "배송", "지역": "방문"}
    # 레뷰는 블로그 체험단이 기본이고, 릴스/쇼츠/클립 등은 제목 끝 "_릴스"나 카드 아이콘으로만 표시한다.
    default_channels = ("blog",)

    def fetch(self) -> list[RawCampaign]:
        return _fetch()

    def from_db_row(self, row: dict) -> RawCampaign:
        raw = super().from_db_row(row)
        # 정제 전 스키마는 category 칸에 페이지 이름("제품"/"지역")을 넣었다.
        if raw.category_raw in self.type_hints:
            raw.type_hint = raw.category_raw
            raw.category_raw = None
        return raw


# 카드 하나 -> dict. 채널 아이콘(블로그/인스타 등)은 대개 img alt 나 클래스명에만 있다.
CARD_JS = """els => els
    .filter(el => el.querySelector('.card-title'))
    .map(el => {
        const img = el.querySelector('img.thumb-img');
        return {
            href: el.getAttribute('href'),
            title: el.querySelector('.card-title')?.textContent?.trim() || null,
            desc: el.querySelector('.card-desc')?.textContent?.trim() || null,
            status: el.querySelector('.card-status')?.textContent?.trim() || '',
            image: img ? (img.currentSrc || img.getAttribute('src') || img.dataset.src || null) : null,
            media: [...el.querySelectorAll('img[alt], [class*="media"], [class*="sns"], [class*="channel"]')]
                .map(x => (x.getAttribute('alt') || x.textContent || '').trim())
                .filter(t => t && t.length <= 20),
            text: el.innerText || ''
        };
    })"""


def _fetch() -> list[RawCampaign]:
    # Playwright는 레뷰에만 필요하니, 설치 안 된 환경에서도 레지스트리 import가 되도록 지연 import
    from playwright.sync_api import sync_playwright

    campaigns: list[RawCampaign] = []
    seen_ids: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()

        if not _login(context):
            browser.close()
            raise RuntimeError("레뷰 로그인에 실패했습니다 (아이디/비밀번호 또는 캡차 확인 필요).")

        page = context.new_page()
        for category in CATEGORIES:
            page.goto(f"{BASE_URL}/category/{category}", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1500)

            cards = page.eval_on_selector_all('a[href^="/campaign/"]', CARD_JS)
            if not cards:
                # 조용히 0건으로 끝나면 아무도 모른다 — 실패로 드러나게 한다
                raise RuntimeError(f"/category/{category} 에서 카드를 하나도 찾지 못했습니다 ({page.url})")

            # 썸네일이 lazy-load라 화면 밖 카드는 src가 비어 있다 (DB상 이미지 채움률 50%).
            # 스크롤로 이미지를 불러온 뒤 다시 읽어 *이미지만* 보충한다 — 스크롤이 목록을 바꿔도
            # 처음 읽은 카드는 그대로 쓴다.
            try:
                for _ in range(8):
                    page.evaluate("window.scrollBy(0, window.innerHeight)")
                    page.wait_for_timeout(250)
                images = {
                    c["href"]: c["image"]
                    for c in page.eval_on_selector_all('a[href^="/campaign/"]', CARD_JS)
                    if c["image"]
                }
                for card in cards:
                    card["image"] = card["image"] or images.get(card["href"])
            except Exception:  # noqa: BLE001 - 이미지 보충은 실패해도 수집은 계속
                pass

            closed = sum(1 for c in cards if _is_closed(c["status"]))
            print(f"[레뷰] /category/{category}: 카드 {len(cards)}개, 모집마감으로 건너뜀 {closed}개, "
                  f"상태 예시 {[c['status'] for c in cards[:3]]}")

            for card in cards:
                m = re.search(r"/campaign/(\d+)", card["href"] or "")
                if not m:
                    continue
                cid = m.group(1)
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)

                if _is_closed(card["status"]):
                    continue  # 종료된 캠페인은 수집하지 않음

                deadline_date = _parse_deadline(card["status"])

                title = card["title"]
                bracket = None
                if title:
                    bm = BRACKET_PREFIX_RE.match(title)
                    if bm:
                        bracket = bm.group(1)
                        title = title[bm.end():].strip() or title

                # /category/지역의 괄호는 지역명, /category/제품의 괄호는 업체명이다.
                region_raw = bracket if category == "지역" else None
                vendor = bracket if category == "제품" else None

                applicant_count = recruit_count = None
                am = APPLICANT_RE.search(card["text"])
                if am:
                    applicant_count = int(am.group(1).replace(",", ""))
                    recruit_count = int(am.group(2))

                image_url = urljoin(BASE_URL, card["image"]) if card["image"] else None

                campaigns.append(
                    RawCampaign(
                        source_url=f"{BASE_URL}/campaign/{cid}",
                        title=title,
                        description=card["desc"],
                        vendor=vendor,
                        image_url=image_url,
                        region_raw=region_raw,
                        deadline_date=deadline_date,
                        recruit_count=recruit_count,
                        applicant_count=applicant_count,
                        # "제품"/"지역"은 페이지 이름일 뿐이라 분류는 normalize가 제목으로 추론한다.
                        category_raw=None,
                        type_hint=category,
                        # 제목 끝의 "_릴스" 같은 채널 표기는 normalize가 제목에서 떼어 channels로 옮긴다.
                        channels_raw=card["media"],
                    )
                )

        browser.close()

    return campaigns


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv("../.env.local")
    items = RevuConnector().fetch()
    print(f"수집된 캠페인: {len(items)}개")
    for c in items[:5]:
        print(c)
