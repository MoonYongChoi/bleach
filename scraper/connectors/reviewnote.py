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
from datetime import datetime, timedelta, timezone
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
API_PAGE_CAP = 100
QUICK_DELAY_MS = 500
FULL_DELAY_MS = 1200
FULL_CRAWL_HOUR_KST = 3  # 매일 이 시각 회차만 지역별 전체 수집 (매시 17분 실행 → 03:17)


def full_crawl_now() -> bool:
    """지역별 전체 수집을 할 회차인지. REVIEWNOTE_FULL=1 이면 시각과 상관없이 전체 수집."""
    import os

    if os.environ.get("REVIEWNOTE_FULL") == "1":
        return True
    return datetime.now(timezone(timedelta(hours=9))).hour == FULL_CRAWL_HOUR_KST  # 사이트가 이 쪽수에서 목록을 끊는 것으로 보인다 (2026-11-12 실행 로그)


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
        """목록 API를 지역별로 나눠 끝까지 읽는다.

        2026-11-12 조사: 응답에 total_count가 있고, 한 목록은 100쪽(1,600건)까지만 준다. 전체(약 1.9만 건)를 받으려면
        city(시/도 이름)로 나누고, 그래도 1,600건을 넘는 시/도(서울·경기 등)는 gugunSelected(시/군/구 id)로 더 나눈다.
        시/도·시/군/구 목록은 사이트가 쓰는 /api/v2/sidos에서 받는다.
        """
        from playwright.sync_api import sync_playwright

        campaigns: list[RawCampaign] = []
        seen: set[str] = set()
        capped: list[str] = []
        requests_made = 0
        full = full_crawl_now()
        # 지역별 전체 수집은 요청이 1,000번을 넘어 빨리 보내면 사이트가 막는다 (2026-11-12, 15분쯤에 403)
        delay_ms = FULL_DELAY_MS if full else QUICK_DELAY_MS

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(LIST_URL, wait_until="networkidle", timeout=45000)

            def call(path: str, params: dict) -> dict:
                nonlocal requests_made
                requests_made += 1
                data = page.evaluate(
                    """async ([path, params]) => {
                        const r = await fetch(path + '?' + new URLSearchParams(params), {credentials: 'same-origin'});
                        return {status: r.status, body: r.status === 200 ? await r.json() : await r.text()};
                    }""",
                    [path, {k: str(v) for k, v in params.items()}],
                )
                if data["status"] != 200:
                    raise RuntimeError(f"{path} {params}: HTTP {data['status']} {str(data['body'])[:120]}")
                return data["body"]

            now_iso = datetime.now(timezone.utc).isoformat()

            def read_list(params: dict) -> bool:
                """한 목록을 끝까지. 100쪽을 다 읽고도 더 있으면(사이트 상한) True.

                지역을 걸면 마감된 캠페인도 섞여 나온다(2026-11-12: 22,923건 중 9,623건) — 마감만 있는 쪽이
                연달아 3번 나오면 그 뒤는 지난 캠페인으로 보고 멈춘다.
                """
                expired_pages = 0
                for page_no in range(API_PAGE_CAP):
                    body = call("/api/v2/campaigns", {"s": "default", "limit": API_LIMIT, "page": page_no, **params})
                    objects = body.get("objects") or []
                    open_count = 0
                    for obj in objects:
                        if (obj.get("applyEndAt") or "9999") < now_iso:
                            continue  # 이미 마감
                        open_count += 1
                        raw = obj_to_raw(obj)
                        if raw and raw.source_url not in seen:
                            seen.add(raw.source_url)
                            campaigns.append(raw)
                    if not objects or not body.get("has_more"):
                        return False
                    expired_pages = expired_pages + 1 if open_count == 0 else 0
                    if expired_pages >= 3:
                        return False
                    page.wait_for_timeout(delay_ms)  # 사이트 부담 줄이기
                return True

            split: list[str] = []
            blocked = None
            try:
                # 지역 없이 본 목록(모집 중만, 최신 1,600건까지) — 매시간은 이것만
                if read_list({}):
                    capped.append("전체")
                if full:
                    sidos = call("/api/v2/sidos", {}) or []
                    for sido in sidos:
                        name = sido.get("name")
                        if not name or not read_list({"city": name}):
                            continue
                        # 100쪽 상한에 걸린 시/도(서울·경기 등) → 시/군/구별로 다시
                        split.append(name)
                        for gugun in sido.get("guguns") or []:
                            if gugun.get("id") is not None and read_list({"city": name, "gugunSelected": gugun["id"]}):
                                capped.append(f"{name} {gugun.get('name')}")
                    capped = [c for c in capped if c != "전체"]  # 전체 목록의 상한은 지역별로 읽어 메웠다
            except RuntimeError as e:
                # 도중에 막혀도 받은 것은 쓴다 — 다만 끝까지 못 읽었으니 종료 처리는 하지 않는다
                blocked = str(e)
                print(f"[리뷰노트] 도중에 멈춤 ({requests_made}번째 요청): {blocked[:160]}")
            browser.close()

        got = len(campaigns)
        # 하루 한 번 전체 수집에서, 막히지 않고 시/군/구까지 상한 없이 다 읽었을 때만 "끝까지 읽음"
        # (목록에서 사라진 캠페인 종료 처리의 조건). 매시간 수집은 최신 1,600건만 보므로 종료 처리하지 않는다.
        self.complete = full and not capped and blocked is None
        print(f"[리뷰노트] {'지역별 전체' if full else '최신 목록'} API {requests_made}회 → 모집 중 캠페인 {got}건"
              + (f", 시/군/구로 나눈 시/도: {split}" if split else "")
              + (f", 그래도 상한에 걸린 목록: {capped[:5]}" if capped else ""))
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
