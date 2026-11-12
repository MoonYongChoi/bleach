"""서울오빠(Seoulouba) 커넥터. 데이터센터 IP는 접속이 막혀 가정용 PC에서만 돈다 (local_only).

구조 메모 (probe.py 조사 2026-10-29, 가정용 PC에서 재조사 2026-11-05):
- 목록: GET https://www.seoulouba.co.kr/campaign/?cat=N&sort=latest — 서버 렌더링, 첫 화면 192개.
  더보기: POST /campaign/ajax/list.ajax.php  {cat, qq, q, q1, q2, ar1, ar2, sort, pt, page, more, rows=36}
  (page는 2부터, more는 이미 받은 개수 = offset). 응답은 같은 <li class="campaign_content"> 조각.
- 상위 cat: 377 방문형 / 383 배송형 / 448 기자단. 세부 cat이 사이트 자체 분류라 category_raw로 쓴다.
- 지역: 방문형 목록을 ar1(권역)/ar2(세부 지역)로 거를 수 있다. 제목 괄호가 "[가산]"처럼 동네 이름뿐인
  경우가 많아, ar2로 받은 목록에서 시/도를 보충한다.
- 카드: <li class="campaign_content">
    <a class="tum_img" href=".../campaign/?c=ID"><img src="...thumb..._260x260.jpg"></a>
    <div class="icon_box"><img alt="네이버블로그" src=".../thum_ch_blog.png"></div>   ← 리뷰 채널
    <div class="icon_tag"><span>방문형</span><span>주말</span></div>               ← 유형
    <strong class="s_campaign_title">[인천/서구] 스튜디오시루아</strong>              ← [지역 또는 유형] 제목
    <span class="basic_blue">헤어스트록 눈썹 or 틴트입술 중 택 1</span>               ← 제공내역
    <div class="d_day"><span> D-day</span></div>   ← "D-n" / "D-day" / 모집이 끝났으면 "마감"
    <div class="recruit"><span>신청 1 <span class="span_gray">/ 모집 5</span></span></div>
- 목록에는 모집이 끝난("마감") 캠페인도 섞여 나온다 → 건너뛴다.
- robots.txt는 전체 Disallow — 사용자 결정(2026-10-29)으로 수집하되 요청 간격을 둔다.
"""

from __future__ import annotations

import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

from connectors.base import Connector, RawCampaign, get_with_retry, split_title_brackets
from regions import resolve_region

BASE_URL = "https://www.seoulouba.co.kr"
LIST_URL = f"{BASE_URL}/campaign/"
AJAX_URL = f"{BASE_URL}/campaign/ajax/list.ajax.php"
HEADERS = {"User-Agent": "Mozilla/5.0 (BleachBot/1.0; +https://bleach.app)"}

TOP_CATEGORIES = {"377": "방문형", "383": "배송형", "448": "기자단"}
# 세부 카테고리 (사이트 분류 이름 그대로 category_raw로; "기타"는 분류 정보가 없어 키워드 추정에 맡긴다)
SUB_CATEGORIES = {
    "378": ("방문형", "맛집"), "379": ("방문형", "여행/숙박"), "380": ("방문형", "뷰티/패션"),
    "510": ("방문형", "스포츠/레저"), "381": ("방문형", "문화/생활"), "382": ("방문형", "테이크아웃"),
    "384": ("배송형", "식품"), "385": ("배송형", "뷰티"), "386": ("배송형", "디지털"), "387": ("배송형", "패션"),
    "388": ("배송형", "생활"), "389": ("배송형", "유아동"), "390": ("배송형", "도서"), "391": ("배송형", "펫"),
}
# 방문형 세부 지역: ar2 -> (ar1, 시/도 보충값). 권역이 시/도 여럿에 걸치면(충청·전라) 보충하지 않는다.
AREAS: dict[str, tuple[str, Optional[str]]] = {
    **{a: ("455", "서울") for a in ("456", "457", "458", "459", "460", "461", "462", "463", "464", "465",
                                     "466", "467", "468", "469", "470", "471", "513")},
    **{a: ("472", "경기") for a in ("473", "474", "476", "477", "514", "515", "516")},
    "475": ("472", "인천"),  # 인천/부천 — 부천은 제목 괄호에서 경기로 잡힌다
    "479": ("478", "대전"), "480": ("478", None), "493": ("478", "세종"),
    "482": ("481", "대구"), "483": ("481", "경북"),
    "485": ("484", "부산"), "486": ("484", "경남"),
    "488": ("487", "광주"), "489": ("487", None),
}
# 세부 지역이 없는 권역
AREA_GROUPS = {"491": "강원", "492": "제주"}

PAGE_ROWS = 36
MAX_PAGES = 60  # 목록 하나당 더보기 상한 (36 x 60 = 2,160건)
DELAY = 1.0

DDAY_RE = re.compile(r"D\s*-\s*(\d+)", re.I)
RECRUIT_RE = re.compile(r"신청\s*([\d,]+)\s*/\s*모집\s*([\d,]+)")
ID_RE = re.compile(r"[?&]c=(\d+)")


def campaign_id(source_url: str) -> Optional[str]:
    m = ID_RE.search(source_url)
    return m.group(1) if m else None


def parse_list(html: str, category_type: str, category_raw: Optional[str] = None) -> list[RawCampaign]:
    """목록(또는 더보기 조각) HTML -> 모집 중인 캠페인. "마감" 카드는 뺀다."""
    soup = BeautifulSoup(html, "html.parser")
    campaigns: list[RawCampaign] = []
    for card in soup.select("li.campaign_content"):
        link = card.select_one("a[href*='campaign/?c=']")
        title_el = card.select_one(".s_campaign_title")
        if not link or not title_el:
            continue
        m = ID_RE.search(link["href"])
        if not m:
            continue

        dday_el = card.select_one(".d_day")
        dday_text = dday_el.get_text(strip=True) if dday_el else ""
        if "마감" in dday_text:
            continue
        dm = DDAY_RE.search(dday_text)
        days_left = int(dm.group(1)) if dm else (0 if "day" in dday_text.lower() else None)

        title, brackets = split_title_brackets(title_el.get_text(strip=True))
        type_tag = card.select_one(".icon_tag span")
        type_hint = (type_tag.get_text(strip=True) if type_tag else None) or (brackets["types"] or [category_type])[0]

        recruit_text = card.select_one(".recruit").get_text(" ", strip=True) if card.select_one(".recruit") else ""
        rm = RECRUIT_RE.search(recruit_text)

        img = card.select_one("a.tum_img img")
        channels = [i.get("alt", "") for i in card.select(".icon_box img")] + brackets["channels"]
        offer = card.select_one(".basic_blue")

        campaigns.append(
            RawCampaign(
                source_url=f"{BASE_URL}/campaign/?c={m.group(1)}",
                title=title,
                description=offer.get_text(strip=True) if offer else None,
                image_url=img.get("src") if img else None,
                region_raw=(brackets["regions"] or [None])[0],
                deadline_days_left=days_left,
                applicant_count=rm.group(1) if rm else None,
                recruit_count=rm.group(2) if rm else None,
                category_raw=category_raw,
                type_hint=type_hint,
                channels_raw=channels,
            )
        )
    return campaigns


def card_count(html: str) -> int:
    return html.count('class="campaign_content"')


def with_area_hint(raw: RawCampaign, hint: Optional[str]) -> RawCampaign:
    """제목 괄호만으로 시/도를 못 정하면 세부 지역 목록에서 알게 된 시/도를 앞에 붙인다 ("가산" -> "서울 가산")."""
    if not hint or resolve_region(raw.region_raw)[0]:
        return raw
    raw.region_raw = f"{hint} {raw.region_raw or ''}".strip()
    return raw


class SeouloubaConnector(Connector):
    key = "seoulouba"
    label = "서울오빠"
    base_url = BASE_URL
    # 데이터센터 IP는 접속 시간초과(GitHub 해외 러너, Vercel 서울 리전 모두 2026-11-05 확인) — 가정용 PC에서만 수집
    local_only = True
    # "촬영"은 채널 아이콘 자리에 오는 기자단 표시라 채널로 보지 않는다 (유형 쪽에서 기자단으로 잡힘)
    type_hints = {"촬영기자단": "기자단", "기자단": "기자단"}
    channel_hints = {"네이버블로그": "blog", "인스타그램": "instagram", "유튜브": "youtube", "릴스": "reels"}

    def __init__(self) -> None:
        self.session: Optional[requests.Session] = None

    def _list(self, cat: str, category_type: str, category_raw: Optional[str] = None,
              ar1: str = "", ar2: str = "") -> list[RawCampaign]:
        """목록 하나를 더보기 끝까지. 한 페이지가 통째로 "마감"이면 그 뒤는 지난 캠페인이라 멈춘다."""
        assert self.session is not None
        params = {"cat": cat, "sort": "latest"}
        if ar1:
            params["ar1"] = ar1
        if ar2:
            params["ar2"] = ar2
        html = get_with_retry(self.session, LIST_URL, params=params).text
        found = parse_list(html, category_type, category_raw)
        offset, page = card_count(html), 2
        if offset < 192:  # 첫 화면이 다 차지 않았으면 더보기가 없다
            return found
        while True:
            if page > MAX_PAGES:
                self.complete = False  # 상한에 걸려 끝까지 못 읽음
                break
            time.sleep(DELAY)
            data = {"cat": cat, "qq": "", "q": "", "q1": "", "q2": "", "ar1": ar1, "ar2": ar2,
                    "sort": "latest", "pt": "", "page": page, "more": offset, "rows": PAGE_ROWS}
            chunk = get_with_retry(self.session, AJAX_URL, method="POST", data=data).text
            n = card_count(chunk)
            if n == 0:
                break
            open_cards = parse_list(chunk, category_type, category_raw)
            found += open_cards
            if not open_cards or n < PAGE_ROWS:
                break
            offset += n
            page += 1
        return found

    def fetch(self) -> list[RawCampaign]:
        self.complete = True  # 목록 하나라도 상한에 걸리면 _list가 False로 바꾼다
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        by_id: dict[str, RawCampaign] = {}

        def add(items: list[RawCampaign]) -> int:
            new = 0
            for raw in items:
                cid = campaign_id(raw.source_url)
                if cid and cid not in by_id:
                    by_id[cid] = raw
                    new += 1
            return new

        # 1) 세부 카테고리 목록 — 사이트 분류를 category_raw로
        for cat, (category_type, name) in SUB_CATEGORIES.items():
            items = self._list(cat, category_type, name)
            print(f"[서울오빠] {category_type}/{name}: 모집 중 {len(items)}건 (신규 {add(items)})")
            time.sleep(DELAY)

        # 2) 상위 목록 — 세부 카테고리에 없던 것(기타·채널 전용)과 기자단 전체
        for cat, category_type in TOP_CATEGORIES.items():
            items = self._list(cat, category_type)
            print(f"[서울오빠] {category_type} 전체: 모집 중 {len(items)}건 (세부 목록에 없던 것 {add(items)})")
            time.sleep(DELAY)

        # 3) 방문형 지역 — 제목 괄호로 시/도를 못 정하는 캠페인에 시/도 보충
        hints: dict[str, Optional[str]] = {}
        for ar2, (ar1, hint) in AREAS.items():
            for raw in self._list("377", "방문형", ar1=ar1, ar2=ar2):
                hints.setdefault(campaign_id(raw.source_url) or "", hint)
            time.sleep(DELAY)
        for ar1, hint in AREA_GROUPS.items():
            for raw in self._list("377", "방문형", ar1=ar1):
                hints.setdefault(campaign_id(raw.source_url) or "", hint)
            time.sleep(DELAY)
        for cid, raw in by_id.items():
            with_area_hint(raw, hints.get(cid))
        print(f"[서울오빠] 지역 목록에서 확인한 방문형 {len(hints)}건")

        return list(by_id.values())


if __name__ == "__main__":
    items = SeouloubaConnector().fetch()
    print(f"수집된 캠페인: {len(items)}개")
    for c in items[:5]:
        print(c)
