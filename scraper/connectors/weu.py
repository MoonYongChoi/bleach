"""위유(WE:U) 체험단 커넥터.

구조 메모 (2026-11-19 probe.py 조사):
- React SPA. 목록 화면(/campaignlist)이 GET https://api.weu.kr/api/v1/user/slot/campaign-winner-trynow
  ?type=just_made&per_page=N&offset=1 을 부른다. per_page=200이면 모집 중 전체(135건)가 한 번에 온다
  (data.total_data / total_page로 끝을 확인한다).
- 항목: id, type("winner"), campaign_title("[경기 광주] 늘here"), winner_campaign_reward(제공 내역, <br> 포함),
  thumbnail("/campaign/images/<hash>.webp" — 상대 경로, 호스트는 화면에 그려진 <img>에서 알아낸다),
  registration_end_date("25/11/2026-23:59:59" = 일/월/연), type_blog_review(["blog"], ["instagram"]),
  campaign_type("방문형"), max_selected(모집 인원), number_of_register(신청자 수), ctg_name("맛집"/"기타"),
  address("경기 광주시 경안동 447"), recruit_type("period"), created_at_sort.
- 정책: robots.txt·ai.txt가 /campaignlist는 허용, 캠페인 상세(/detailPage/ 등)는 막는다.
  → 목록 API 값만 쓰고 상세 페이지는 열지 않는다 (원문 링크만 건다). 2026-11-19 사용자 결정.
"""

from __future__ import annotations

import html
import json
import re
from datetime import date
from typing import Optional

from connectors.base import Connector, RawCampaign, split_title_brackets

BASE_URL = "https://weu.kr"
LIST_URL = f"{BASE_URL}/campaignlist"
API_URL = "https://api.weu.kr/api/v1/user/slot/campaign-winner-trynow"
PER_PAGE = 200
MAX_PAGES = 20
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"

END_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
TAG_RE = re.compile(r"<[^>]+>")


def parse_end_date(value: Optional[str]) -> Optional[date]:
    """"25/11/2026-23:59:59" -> 2026-11-25"""
    m = END_DATE_RE.match(value or "")
    if not m:
        return None
    day, month, year = (int(g) for g in m.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def clean_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = TAG_RE.sub(" ", html.unescape(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def item_to_raw(item: dict, image_base: Optional[str], today: Optional[date] = None) -> Optional[RawCampaign]:
    """목록 API 항목 하나 -> RawCampaign. 마감일이 지난 항목은 None."""
    cid = item.get("id")
    raw_title = (item.get("campaign_title") or "").strip()
    if not cid or not raw_title:
        return None
    deadline = parse_end_date(item.get("registration_end_date"))
    if deadline and today and deadline < today:
        return None

    title, brackets = split_title_brackets(raw_title)
    visit = (item.get("campaign_type") or "").startswith("방문")
    address = " ".join((item.get("address") or "").split()[:2])
    region_raw = (address or (brackets["regions"] or [None])[0]) if visit else None

    thumb = item.get("thumbnail") or item.get("cover_image") or ""
    if thumb.startswith("/") and image_base:
        thumb = image_base + thumb
    elif not thumb.startswith("http"):
        thumb = ""

    description = clean_text(item.get("winner_campaign_reward"))
    kind = item.get("type") or "winner"
    return RawCampaign(
        source_url=f"{BASE_URL}/detailPage/{cid}?type={kind}",
        title=title or raw_title,
        description=description,
        image_url=thumb or None,
        region_raw=region_raw,
        deadline_date=deadline,
        recruit_count=item.get("max_selected"),
        applicant_count=item.get("number_of_register"),
        category_raw=item.get("ctg_name"),
        type_hint=item.get("campaign_type"),
        channels_raw=[str(c) for c in (item.get("type_blog_review") or [])] + brackets["channels"],
        is_payback="페이백" in raw_title or "페이백" in (description or ""),
    )


class WeuConnector(Connector):
    key = "weu"
    label = "위유"
    base_url = BASE_URL
    # API는 위유 화면 안에서 부르는 것과 같은 방식(브라우저 fetch)으로 부른다. 썸네일 호스트도 화면에서 알아낸다.
    needs_browser = True
    browser_user_agent = UA
    type_hints = {"방문형": "방문", "배송형": "배송", "기자단": "기자단", "구매형": "구매"}
    default_channels = ("blog",)

    def fetch(self) -> list[RawCampaign]:
        from playwright.sync_api import sync_playwright

        from normalize import today_kst

        self.complete = False
        items: list[dict] = []
        image_base: Optional[str] = None
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=UA, locale="ko-KR")
            requested: list[str] = []
            page.on("request", lambda r: requested.append(r.url) if "/campaign/images/" in r.url else None)
            page.goto(LIST_URL, wait_until="networkidle", timeout=45000)
            # 썸네일 상대 경로(/campaign/images/...)가 붙는 호스트: 화면이 실제로 받은 이미지 주소에서 찾는다
            srcs = page.eval_on_selector_all("img", "els => els.map(e => e.currentSrc || e.src)")
            for src in requested + srcs:
                if src and "/campaign/images/" in src and src.startswith("http"):
                    image_base = src[: src.index("/campaign/images/")]
                    break
            print(f"[위유] 썸네일 호스트: {image_base or '못 찾음'} (화면 이미지 {len(srcs)}개)")

            total = None
            for page_no in range(1, MAX_PAGES + 1):
                url = f"{API_URL}?type=just_made&per_page={PER_PAGE}&offset={page_no}"
                res = page.evaluate(
                    "async (u) => { const r = await fetch(u); return {s: r.status, t: await r.text()}; }", url
                )
                if res["s"] != 200:
                    print(f"[위유] offset={page_no}: HTTP {res['s']} — 여기서 멈춤")
                    break
                data = (json.loads(res["t"]).get("data") or {})
                rows = data.get("data") or []
                total = data.get("total_data")
                items.extend(rows)
                if not rows or page_no >= (data.get("total_page") or 1):
                    self.complete = total is not None and len(items) >= total
                    break
                page.wait_for_timeout(500)
            browser.close()

        today = today_kst()
        campaigns: list[RawCampaign] = []
        seen: set[str] = set()
        for item in items:
            raw = item_to_raw(item, image_base, today)
            if raw and raw.source_url not in seen:
                seen.add(raw.source_url)
                campaigns.append(raw)
        print(f"[위유] API {len(items)}건 (사이트 표시 전체 {total}) → 모집 중 {len(campaigns)}건, 끝까지 읽음={self.complete}")
        if not campaigns:
            raise RuntimeError("위유 목록 API에서 캠페인을 하나도 읽지 못했습니다")
        return campaigns


if __name__ == "__main__":
    for c in WeuConnector().fetch()[:5]:
        print(c)
