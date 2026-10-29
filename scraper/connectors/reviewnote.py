"""리뷰노트(Reviewnote) 커넥터.

구조 메모 (2026-10-07 조사, 10-28 필드 확인):
- https://www.reviewnote.co.kr/campaigns 는 Next.js SSR 페이지로,
  <script id="__NEXT_DATA__">에 props.pageProps.data.objects 배열이 그대로 들어있다.
  requests만으로 충분 (JS 실행 불필요).
- 객체 필드: id, title, offer(제공내역), city(시/도), sido.name(시/군/구 — 이름이 헷갈림),
  applyEndAt(UTC ISO), infNum(모집), applicantCount(신청), category.title, imageKey,
  sort(VISIT/DELIVERY/...: 유형), channel(BLOG/...: 리뷰 채널), paybackPlatform(구매 후 환급형이면 값 있음)
- 한계: ?page= 쿼리는 서버에서 무시되고 항상 최신 96개만 내려온다. 그 이상(무한스크롤)은 별도
  내부 API를 호출해야 해서 보류 — 필요해지면 네트워크 탭에서 XHR 엔드포인트를 다시 조사할 것.
"""

from __future__ import annotations

import json
import re
from typing import Optional
from urllib.parse import quote

import requests

from connectors.base import Connector, RawCampaign

LIST_URL = "https://www.reviewnote.co.kr/campaigns"
DETAIL_URL = "https://www.reviewnote.co.kr/campaigns/{id}"
HEADERS = {"User-Agent": "Mozilla/5.0 (BleachBot/1.0; +https://bleach.app)"}

IMAGE_CDN = "https://img.reviewnote.cloud/cdn-cgi/image/width=640,quality=60,format=auto,fit=scale-down/"
FIREBASE_IMAGE_URL = (
    "https://firebasestorage.googleapis.com/v0/b/reviewnote-e92d9.appspot.com/o/{key}?alt=media"
)

NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def _image_url(image_key: Optional[str]) -> Optional[str]:
    if not image_key:
        return None
    # Firebase Storage는 객체 키 전체를 percent-encoding 해야 한다 ('/', 공백, 한글 등).
    return IMAGE_CDN + FIREBASE_IMAGE_URL.format(key=quote(image_key, safe=""))


class ReviewnoteConnector(Connector):
    key = "reviewnote"
    label = "리뷰노트"
    base_url = "https://www.reviewnote.co.kr"
    type_hints = {
        "VISIT": "방문",
        "DELIVERY": "배송",
        "PURCHASE": "구매",
        "PAYBACK": "구매",
        "REPORTER": "기자단",
        "PRESS": "기자단",
    }
    channel_hints = {
        "BLOG": "blog",
        "NAVER_BLOG": "blog",
        "INSTAGRAM": "instagram",
        "INSTA": "instagram",
        "REELS": "reels",
        "YOUTUBE": "youtube",
        "SHORTS": "shorts",
        "TIKTOK": "tiktok",
        "CLIP": "clip",
        "NAVER_CLIP": "clip",
    }

    def fetch(self) -> list[RawCampaign]:
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

            channel = obj.get("channel")
            channels = channel if isinstance(channel, list) else [channel] if channel else []

            campaigns.append(
                RawCampaign(
                    source_url=DETAIL_URL.format(id=cid),
                    title=title or offer or None,
                    description=offer or None,
                    image_url=_image_url(obj.get("imageKey")),
                    # 필드명이 헷갈리게 되어 있다: city = 시/도("서울"), sido.name = 시/군/구("강남구")
                    region_sido=obj.get("city"),
                    region_gugun=(obj.get("sido") or {}).get("name"),
                    # ISO(UTC) 문자열 그대로 넘기면 normalize가 KST 날짜로 바꾼다.
                    deadline_date=obj.get("applyEndAt"),
                    recruit_count=obj.get("infNum"),
                    applicant_count=obj.get("applicantCount"),
                    category_raw=(obj.get("category") or {}).get("title"),
                    type_hint=obj.get("sort"),
                    channels_raw=[str(c) for c in channels],
                    is_payback=bool(obj.get("paybackPlatform")),
                )
            )

        return campaigns

    def from_db_row(self, row: dict) -> RawCampaign:
        raw = super().from_db_row(row)
        # 예전 스크래퍼는 제목 뒤에 " - 제공내역"을 붙여 저장했다.
        desc = row.get("description")
        if desc and raw.title and raw.title.endswith(f" - {desc}") and len(raw.title) > len(desc) + 3:
            raw.title = raw.title[: -(len(desc) + 3)]
        # 리뷰노트는 시/도·시군구가 이미 나뉘어 있으므로 원본 텍스트로 다시 해석하지 않는다.
        raw.region_raw = None
        raw.region_sido = row.get("region_sido")
        raw.region_gugun = row.get("region_gugun")
        return raw


if __name__ == "__main__":
    items = ReviewnoteConnector().fetch()
    print(f"수집된 캠페인: {len(items)}개")
    for c in items[:5]:
        print(c)
