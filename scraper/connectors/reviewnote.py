"""리뷰노트(Reviewnote) 커넥터.

구조 메모 (2026-10-07 조사, 10-28 필드 확인):
- https://www.reviewnote.co.kr/campaigns 는 Next.js SSR 페이지로,
  <script id="__NEXT_DATA__">에 props.pageProps.data.objects 배열이 그대로 들어있다.
  requests만으로 충분 (JS 실행 불필요).
- 객체 필드: id, title, offer(제공내역), city(시/도), sido.name(시/군/구 — 이름이 헷갈림),
  applyEndAt(UTC ISO), infNum(모집), applicantCount(신청), category.title, imageKey,
  sort(VISIT/DELIVERY/...: 유형), channel(BLOG/...: 리뷰 채널), paybackPlatform(구매 후 환급형이면 값 있음)
- 한계: ?page= 쿼리는 서버에서 무시되고 항상 최신 96개만 내려온다.
- 2026-11-06 probe.py --js-api 조사: 무한스크롤은 GET /api/v2/campaigns?page=N&limit=16&s=default...
  → {page, objects, has_more}. objects는 위 __NEXT_DATA__와 같은 모양이다. 사이트 밖(requests)에서
  부르면 403이라, 브라우저로 목록을 연 뒤 그 페이지 안에서 fetch로 부른다. 실패하면 첫 96개로 대신한다.
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


API_LIMIT = 16  # 사이트 화면과 같게 — 100을 주면 첫 쪽(96개)과 둘째 쪽이 겹쳐 멈췄다 (2026-11-06)
API_MAX_PAGES = 600
API_PAGE_CAP = 100  # 사이트가 이 쪽수에서 목록을 끊는 것으로 보인다 (2026-11-12 실행 로그)


def obj_to_raw(obj: dict) -> Optional[RawCampaign]:
    """목록 객체(__NEXT_DATA__ 또는 /api/v2/campaigns) 하나 -> RawCampaign."""
    cid = obj.get("id")
    if cid is None:
        return None
    # 제목과 제공내역(offer)은 따로 저장한다 — 예전엔 "제목 - 제공내역"으로 합쳐서
    # 카드 제목이 길어지고 description과 중복됐다.
    title = (obj.get("title") or "").strip()
    offer = (obj.get("offer") or "").strip()
    channel = obj.get("channel")
    channels = channel if isinstance(channel, list) else [channel] if channel else []
    return RawCampaign(
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


class ReviewnoteConnector(Connector):
    key = "reviewnote"
    label = "리뷰노트"
    base_url = "https://www.reviewnote.co.kr"
    # 상세 페이지 정적 HTML에는 사이트 공통 틀(483자)만 있고 캠페인 내용은 JS가 그린다 (2026-10-31 검수)
    verify_with_browser = True
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
        self.complete = False
        try:
            return self._fetch_api()
        except Exception as e:  # noqa: BLE001 - API가 막혀도 첫 화면 96개는 받는다
            print(f"[리뷰노트] 목록 API 수집 실패 → 첫 화면만: {type(e).__name__}: {e}")
            return self._fetch_first_page()

    def _fetch_first_page(self) -> list[RawCampaign]:
        resp = requests.get(LIST_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        m = NEXT_DATA_RE.search(resp.text)
        if not m:
            return []
        data = json.loads(m.group(1))
        objects = data.get("props", {}).get("pageProps", {}).get("data", {}).get("objects", [])
        return [r for r in (obj_to_raw(o) for o in objects) if r]

    def _fetch_api(self) -> list[RawCampaign]:
        from playwright.sync_api import sync_playwright

        campaigns: list[RawCampaign] = []
        seen: set[str] = set()
        pages = 0
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(LIST_URL, wait_until="networkidle", timeout=45000)
            for page_no in range(API_MAX_PAGES):
                data = page.evaluate(
                    """async ([n, limit]) => {
                        const q = new URLSearchParams({s: 'default', limit, page: n});
                        const r = await fetch('/api/v2/campaigns?' + q, {credentials: 'same-origin'});
                        return {status: r.status, body: r.status === 200 ? await r.json() : await r.text()};
                    }""",
                    [page_no, API_LIMIT],
                )
                if data["status"] != 200:
                    raise RuntimeError(f"page={page_no}: HTTP {data['status']} {str(data['body'])[:120]}")
                body = data["body"] or {}
                objects = body.get("objects") or []
                pages += 1
                new = 0
                for obj in objects:
                    raw = obj_to_raw(obj)
                    if raw and raw.source_url not in seen:
                        seen.add(raw.source_url)
                        campaigns.append(raw)
                        new += 1
                if not objects or not body.get("has_more"):
                    # 2026-11-12: 사이트가 100쪽(1,600건)에서 has_more=false를 준다 — 목록 끝이 아니라 상한일 수 있어
                    # 그 경우는 끝까지 읽었다고 보지 않는다 (사라진 캠페인을 잘못 내리지 않게)
                    self.complete = pages < API_PAGE_CAP
                    if not self.complete:
                        print(f"[리뷰노트] {pages}쪽에서 목록이 끝남 — 사이트 상한으로 보고 종료 처리는 하지 않음")
                    break
                if new == 0:
                    break
                page.wait_for_timeout(300)  # 사이트 부담 줄이기
            browser.close()
        print(f"[리뷰노트] 목록 API {pages}쪽 → 캠페인 {len(campaigns)}건")
        if not campaigns:
            raise RuntimeError("목록 API에서 캠페인을 하나도 받지 못함")
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
