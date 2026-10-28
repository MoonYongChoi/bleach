"""레뷰(Revu) 체험단 스크래퍼.

레뷰는 AngularJS SPA라 서버 렌더링 HTML에 데이터가 없고, 카테고리 전체 목록은
로그인한 사용자에게만 열린다 (비로그인 시 /login으로 리다이렉트됨).
그래서 이 스크래퍼만 Playwright로 실제 로그인 후 렌더링된 DOM을 읽는다.

환경변수 REVU_ID / REVU_PW 필요 (.env.local).

구조 메모 (2026-10-07 조사):
- 로그인: POST 없이 /login 페이지의 input[name=email], input[name=password] +
  "로그인" 버튼 클릭으로 처리 (reCAPTCHA는 이번 조사에서는 나타나지 않았음).
- 목록: /category/제품, /category/지역 (로그인 필요). 카드 구조:
    <a href="/campaign/ID">
      ...
      <p class="card-title">제목</p>
      ...
      <strong class="card-status">N일 남음 | 마감 임박 | 모집마감 | ...</strong>
      ...
    </a>
- 정확한 마감 "일수"만 주어지고 날짜/지역은 구조화되어 있지 않음 → 제목에서
  "[지역]" 괄호 프리픽스를 best-effort로 추출.
"""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from typing import Optional

from playwright.sync_api import sync_playwright

from regions import resolve_region

BASE_URL = "https://www.revu.net"
CATEGORIES = ["제품", "지역"]

REGION_PREFIX_RE = re.compile(r"^\[([^\]]+)\]")
DAYS_LEFT_RE = re.compile(r"(\d+)\s*일\s*남음")


def _login(context) -> bool:
    email = os.environ.get("REVU_ID")
    pw = os.environ.get("REVU_PW")
    if not email or not pw:
        raise RuntimeError("REVU_ID / REVU_PW 환경변수가 설정되어 있지 않습니다.")

    page = context.new_page()
    page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=30000)
    page.fill("input[name=email]", email)
    page.fill("input[name=password]", pw)
    page.click('button:has-text("로그인")')
    page.wait_for_timeout(2500)

    logged_in = page.locator('a[href="/login"]').count() == 0
    page.close()
    return logged_in


def _parse_deadline(status_text: str) -> Optional[date]:
    status_text = status_text.strip()
    if "모집마감" in status_text or "마감완료" in status_text:
        return None  # 종료된 캠페인은 수집하지 않음
    m = DAYS_LEFT_RE.search(status_text)
    if m:
        return date.today() + timedelta(days=int(m.group(1)))
    if "마감" in status_text:  # "마감 임박" 등 정확한 일수 없음 → 오늘로 간주
        return date.today()
    return None


def fetch_campaigns() -> list[dict]:
    campaigns: list[dict] = []
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

            cards = page.eval_on_selector_all(
                'a[href^="/campaign/"]',
                """els => els
                    .filter(el => el.querySelector('.card-title'))
                    .map(el => ({
                        href: el.getAttribute('href'),
                        title: el.querySelector('.card-title')?.textContent?.trim() || null,
                        status: el.querySelector('.card-status')?.textContent?.trim() || ''
                    }))""",
            )

            for card in cards:
                m = re.search(r"/campaign/(\d+)", card["href"] or "")
                if not m:
                    continue
                cid = m.group(1)
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)

                deadline_date = _parse_deadline(card["status"])
                if deadline_date is None and card["status"]:
                    # 마감 관련 문구가 아예 없으면(예: 신청자 수 표기 등) 그대로 두되,
                    # "모집마감"류는 _parse_deadline에서 이미 걸러짐.
                    pass

                title = card["title"]
                region = None
                if title:
                    rm = REGION_PREFIX_RE.match(title)
                    if rm:
                        region = rm.group(1)
                region_sido, region_gugun = resolve_region(region)

                campaigns.append(
                    {
                        "platform": "레뷰",
                        "title": title,
                        "region_sido": region_sido,
                        "region_gugun": region_gugun,
                        "deadline_date": deadline_date,
                        "announce_date": None,
                        "source_url": f"{BASE_URL}/campaign/{cid}",
                        "category": category,
                        "description": None,
                        "image_url": None,
                        "vendor": None,
                        "recruit_count": None,
                        "applicant_count": None,
                    }
                )

        browser.close()

    return campaigns


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv("../.env.local")
    items = fetch_campaigns()
    print(f"수집된 캠페인: {len(items)}개")
    for c in items[:5]:
        print(c)
