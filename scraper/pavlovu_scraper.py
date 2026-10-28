"""파블로(Pavlovu) 체험단 스크래퍼.

구조 메모 (2026-10-07 조사):
- 목록: https://pavlovu.com/review_campaign_list.php?page=N  (서버 렌더링, requests만으로 충분)
  페이지당 약 70개, page=1..약23까지 존재(사이트 상황에 따라 변동)
- 카드 마크업: <div class="pvc">...<a class="pvc_tx" href="review_campaign.php?cp_id=ID">
    <strong>제목</strong>
    <span class="pvc_store_row"><span class="pvc_store">업체명</span><span class="pvc_deadline">D-4</span></span>
    <span class="pvc_pl"><i>채널</i><span class="pvc_pn">지역 · 카테고리</span>...</span>
  </a>
- 정확한 마감일(날짜)은 상세페이지에서 "신청기간 MM.DD(요일) ~ MM.DD(요일)" 텍스트로 파싱.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://pavlovu.com"
LIST_URL = f"{BASE_URL}/review_campaign_list.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (BleachBot/1.0; +https://bleach.app)"}


def _parse_deadline_from_detail(cp_id: str) -> Optional[date]:
    """상세 페이지의 '신청기간 10.07(수) ~ 10.11(일)' 텍스트에서 종료일을 파싱한다."""
    try:
        resp = requests.get(
            f"{BASE_URL}/review_campaign.php",
            params={"cp_id": cp_id},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None

    m = re.search(r"신청기간\s*(\d{1,2})\.(\d{1,2})\([^)]+\)\s*~\s*(\d{1,2})\.(\d{1,2})\(", resp.text)
    if not m:
        return None

    end_month, end_day = int(m.group(3)), int(m.group(4))
    today = date.today()
    year = today.year
    # 연말/연초 경계: 종료월이 현재월보다 많이 작으면 다음 해로 간주
    if end_month < today.month - 6:
        year += 1
    try:
        return date(year, end_month, end_day)
    except ValueError:
        return None


def fetch_campaigns(max_pages: int = 5, with_exact_deadline: bool = True) -> list[dict]:
    """마감임박순 목록을 긁어서 표준 스키마 dict 리스트로 반환."""
    campaigns: list[dict] = []

    for page in range(1, max_pages + 1):
        resp = requests.get(LIST_URL, params={"page": page}, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        cards = soup.select("li.pvli div.pvc")
        if not cards:
            break

        for card in cards:
            link = card.select_one("a.pvc_tx")
            if not link or not link.get("href"):
                continue

            href = link["href"]
            m = re.search(r"cp_id=(\d+)", href)
            if not m:
                continue
            cp_id = m.group(1)
            source_url = f"{BASE_URL}/review_campaign.php?cp_id={cp_id}"

            title_el = link.select_one("strong")
            title = title_el.get_text(strip=True) if title_el else None
            store_el = link.select_one(".pvc_store")
            if store_el and title:
                title = f"[{store_el.get_text(strip=True)}] {title}"

            region_cat = link.select_one(".pvc_pn")
            region_raw, category = None, None
            if region_cat:
                parts = region_cat.get_text(strip=True).split("·")
                region_raw = parts[0].strip() if len(parts) > 0 else None
                category = parts[1].strip() if len(parts) > 1 else None

            deadline_date = _parse_deadline_from_detail(cp_id) if with_exact_deadline else None

            campaigns.append(
                {
                    "platform": "파블로",
                    "title": title,
                    "region_sido": None,
                    "region_gugun": region_raw,
                    "deadline_date": deadline_date,
                    "announce_date": None,
                    "source_url": source_url,
                    "category": category,
                }
            )

    return campaigns


if __name__ == "__main__":
    items = fetch_campaigns(max_pages=1)
    print(f"수집된 캠페인: {len(items)}개")
    for c in items[:5]:
        print(c)
