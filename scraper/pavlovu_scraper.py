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
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from normalize import today_kst

BASE_URL = "https://pavlovu.com"
LIST_URL = f"{BASE_URL}/review_campaign_list.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (BleachBot/1.0; +https://bleach.app)"}


class _Detail:
    def __init__(self):
        self.deadline_date: Optional[date] = None
        self.description: Optional[str] = None
        self.recruit_count: Optional[int] = None
        self.applicant_count: Optional[int] = None


def _parse_detail(cp_id: str) -> _Detail:
    """상세 페이지에서 정확한 마감일, '제공내역', 모집/대기 인원을 파싱한다.

    모집·대기 인원은 "대기 3명 · 남은 자리 10명"과 별도로 "모집\n10명" 블록이
    있다 — 지원률은 사용자 합의대로 대기인원 ÷ 모집인원(recruit_count)으로 낸다.
    """
    detail = _Detail()
    try:
        resp = requests.get(
            f"{BASE_URL}/review_campaign.php",
            params={"cp_id": cp_id},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return detail

    m = re.search(r"신청기간\s*(\d{1,2})\.(\d{1,2})\([^)]+\)\s*~\s*(\d{1,2})\.(\d{1,2})\(", resp.text)
    if m:
        end_month, end_day = int(m.group(3)), int(m.group(4))
        today = today_kst()
        year = today.year
        # 연말/연초 경계: 종료월이 현재월보다 많이 작으면 다음 해로 간주
        if end_month < today.month - 6:
            year += 1
        try:
            detail.deadline_date = date(year, end_month, end_day)
        except ValueError:
            detail.deadline_date = None

    soup = BeautifulSoup(resp.text, "html.parser")
    lines = soup.get_text("\n", strip=True).split("\n")
    for i, line in enumerate(lines):
        if line == "제공내역" and i + 1 < len(lines):
            detail.description = lines[i + 1]
            break

    wait_m = re.search(r"대기\s*(\d+)\s*명\s*·\s*남은\s*자리\s*\d+\s*명", resp.text)
    if wait_m:
        detail.applicant_count = int(wait_m.group(1))

    for i, line in enumerate(lines):
        if line == "모집" and i + 1 < len(lines):
            dm = re.match(r"(\d+)\s*명", lines[i + 1])
            if dm:
                detail.recruit_count = int(dm.group(1))
            break

    return detail


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
            vendor = store_el.get_text(strip=True) if store_el else None
            # 상세페이지 요청이 실패했을 때 쓸 목록의 "D-4" / "D-day"
            dday_el = link.select_one(".pvc_deadline")
            days_left = None
            if dday_el:
                dday_text = dday_el.get_text(strip=True)
                dm = re.search(r"D-(\d+)", dday_text)
                if dm:
                    days_left = int(dm.group(1))
                elif "day" in dday_text.lower() or "오늘" in dday_text:
                    days_left = 0

            region_cat = link.select_one(".pvc_pn")
            region_raw, category = None, None
            if region_cat:
                parts = region_cat.get_text(strip=True).split("·")
                region_raw = parts[0].strip() if len(parts) > 0 else None
                category = parts[1].strip() if len(parts) > 1 else None

            # lazy-load 이미지는 src에 플레이스홀더가 있고 실제 주소는 data-src 쪽에 있다.
            image_el = card.select_one(".pvc_im img")
            image_src = None
            if image_el:
                image_src = image_el.get("data-src") or image_el.get("data-original") or image_el.get("src")
            image_url = urljoin(BASE_URL, image_src) if image_src else None

            detail = _parse_detail(cp_id) if with_exact_deadline else _Detail()

            campaigns.append(
                {
                    "platform": "파블로",
                    "title": title,
                    "region_raw": region_raw,
                    "deadline_date": detail.deadline_date,
                    "deadline_days_left": days_left,
                    "announce_date": None,
                    "source_url": source_url,
                    "category_raw": category,
                    "description": detail.description,
                    "image_url": image_url,
                    "vendor": vendor,
                    "recruit_count": detail.recruit_count,
                    "applicant_count": detail.applicant_count,
                }
            )

    return campaigns


if __name__ == "__main__":
    items = fetch_campaigns(max_pages=1)
    print(f"수집된 캠페인: {len(items)}개")
    for c in items[:5]:
        print(c)
