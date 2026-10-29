"""레뷰(Revu) 체험단 스크래퍼.

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

from playwright.sync_api import sync_playwright

from normalize import today_kst

BASE_URL = "https://www.revu.net"
CATEGORIES = ["제품", "지역"]

BRACKET_PREFIX_RE = re.compile(r"^\[([^\]]+)\]\s*")
DAYS_LEFT_RE = re.compile(r"(\d+)\s*일\s*남음")
APPLICANT_RE = re.compile(r"신청\s*([\d,]+)\s*/\s*(\d+)\s*명")


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
                        desc: el.querySelector('.card-desc')?.textContent?.trim() || null,
                        status: el.querySelector('.card-status')?.textContent?.trim() || '',
                        image: el.querySelector('img.thumb-img')?.getAttribute('src') || null,
                        text: el.innerText || ''
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
                    {
                        "platform": "레뷰",
                        "title": title,
                        "region_raw": region_raw,
                        "deadline_date": deadline_date,
                        "announce_date": None,
                        "source_url": f"{BASE_URL}/campaign/{cid}",
                        # "제품"/"지역"은 페이지 이름일 뿐이라 분류는 normalize가 제목으로 추론한다.
                        "category_raw": None,
                        "type_hint": category,
                        "description": card["desc"],
                        "image_url": image_url,
                        "vendor": vendor,
                        "recruit_count": recruit_count,
                        "applicant_count": applicant_count,
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
