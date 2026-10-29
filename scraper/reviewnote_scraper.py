"""리뷰노트(Reviewnote) 체험단 스크래퍼.

구조 메모 (2026-10-07 조사):
- https://www.reviewnote.co.kr/campaigns 는 Next.js SSR 페이지로,
  <script id="__NEXT_DATA__">에 props.pageProps.data.objects 배열이 그대로 들어있다.
  requests만으로 충분 (JS 실행 불필요).
- 현재 확인된 한계: 이 엔드포인트의 ?page= 쿼리는 서버에서 무시되고 항상 같은
  최신 96개(total_count)만 내려온다. 그 이상(무한스크롤)은 별도 내부 API를
  호출해야 하는데, 이번 MVP 범위에서는 "최신 96개"만으로 충분하다고 보고
  보류함 — 필요해지면 네트워크 탭에서 실제 XHR 엔드포인트를 다시 조사할 것.
"""

from __future__ import annotations

import json
import re
from typing import Optional
from urllib.parse import quote

import requests

LIST_URL = "https://www.reviewnote.co.kr/campaigns"
DETAIL_URL = "https://www.reviewnote.co.kr/campaigns/{id}"
HEADERS = {"User-Agent": "Mozilla/5.0 (BleachBot/1.0; +https://bleach.app)"}

IMAGE_CDN = "https://img.reviewnote.cloud/cdn-cgi/image/width=640,quality=60,format=auto,fit=scale-down/"
FIREBASE_IMAGE_URL = (
    "https://firebasestorage.googleapis.com/v0/b/reviewnote-e92d9.appspot.com/o/{key}?alt=media"
)


def _image_url(image_key: Optional[str]) -> Optional[str]:
    if not image_key:
        return None
    # Firebase Storage는 객체 키 전체를 percent-encoding 해야 한다 ('/', 공백, 한글 등).
    return IMAGE_CDN + FIREBASE_IMAGE_URL.format(key=quote(image_key, safe=""))

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S
)


def fetch_campaigns() -> list[dict]:
    resp = requests.get(LIST_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    m = NEXT_DATA_RE.search(resp.text)
    if not m:
        return []

    data = json.loads(m.group(1))
    objects = data.get("props", {}).get("pageProps", {}).get("data", {}).get("objects", [])

    campaigns = []
    for obj in objects:
        cid = obj.get("id")
        if cid is None:
            continue

        # 제목과 제공내역(offer)은 따로 저장한다 — 예전엔 "제목 - 제공내역"으로 합쳐서
        # 카드 제목이 길어지고 description과 중복됐다.
        title = (obj.get("title") or "").strip()
        offer = (obj.get("offer") or "").strip()

        # 필드명이 헷갈리게 되어 있다: city = 시/도("서울"), sido.name = 시/군/구("강남구")
        sido = obj.get("sido") or {}

        campaigns.append(
            {
                "platform": "리뷰노트",
                "title": title or offer or None,
                "region_sido": obj.get("city"),
                "region_gugun": sido.get("name"),
                # ISO(UTC) 문자열 그대로 넘기면 normalize가 KST 날짜로 바꾼다.
                "deadline_date": obj.get("applyEndAt"),
                "announce_date": None,
                "source_url": DETAIL_URL.format(id=cid),
                "category_raw": (obj.get("category") or {}).get("title"),
                "type_hint": obj.get("sort"),
                "description": offer or None,
                "image_url": _image_url(obj.get("imageKey")),
                "vendor": None,
                "recruit_count": obj.get("infNum"),
                "applicant_count": obj.get("applicantCount"),
            }
        )

    return campaigns


if __name__ == "__main__":
    items = fetch_campaigns()
    print(f"수집된 캠페인: {len(items)}개")
    for c in items[:5]:
        print(c)
