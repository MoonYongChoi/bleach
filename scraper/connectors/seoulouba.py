"""서울오빠(Seoulouba) 커넥터.

구조 메모 (2026-10-29 probe.py 조사):
- 목록: https://www.seoulouba.co.kr/campaign/?cat=N — 서버 렌더링, requests로 충분. 한 페이지 192개.
  cat=377 방문형 / cat=383 배송형 / cat=448 기자단(촬영기자단)
- 카드: <li class="campaign_content">
    <a class="tum_img" href=".../campaign/?c=ID"><img src="...thumb..._260x260.jpg"></a>
    <div class="icon_box"><img alt="네이버블로그" src=".../thum_ch_blog.png"></div>   ← 리뷰 채널
    <div class="icon_tag"><span>방문형</span></div>                                  ← 유형
    <strong class="s_campaign_title">[인천/서구] 스튜디오시루아</strong>              ← [지역 또는 유형] 제목
    <span class="basic_blue">헤어스트록 눈썹 or 틴트입술 중 택 1</span>               ← 제공내역
    <div class="d_day"><span> D-day</span></div>
    <div class="recruit"><span>신청 1 <span class="span_gray">/ 모집 5</span></span></div>
- 더 보기는 /campaign/ajax/list.ajax.php (아직 첫 페이지 192개만 수집).
- robots.txt는 전체 Disallow — 사용자 결정(2026-10-29)으로 수집하되 요청 간격을 둔다.
"""

from __future__ import annotations

import re
import time

import requests
from bs4 import BeautifulSoup

from connectors.base import Connector, RawCampaign, get_with_retry, split_title_brackets

BASE_URL = "https://www.seoulouba.co.kr"
LIST_URL = f"{BASE_URL}/campaign/"
HEADERS = {"User-Agent": "Mozilla/5.0 (BleachBot/1.0; +https://bleach.app)"}
CATEGORIES = {"377": "방문형", "383": "배송형", "448": "기자단"}

DDAY_RE = re.compile(r"D\s*-\s*(\d+)", re.I)
RECRUIT_RE = re.compile(r"신청\s*([\d,]+)\s*/\s*모집\s*([\d,]+)")


def parse_list(html: str, category_type: str) -> list[RawCampaign]:
    soup = BeautifulSoup(html, "html.parser")
    campaigns: list[RawCampaign] = []
    for card in soup.select("li.campaign_content"):
        link = card.select_one("a[href*='campaign/?c=']")
        title_el = card.select_one(".s_campaign_title")
        if not link or not title_el:
            continue
        m = re.search(r"[?&]c=(\d+)", link["href"])
        if not m:
            continue

        title, brackets = split_title_brackets(title_el.get_text(strip=True))
        type_tag = card.select_one(".icon_tag span")
        type_hint = (type_tag.get_text(strip=True) if type_tag else None) or (brackets["types"] or [category_type])[0]

        dday_text = card.select_one(".d_day").get_text(strip=True) if card.select_one(".d_day") else ""
        dm = DDAY_RE.search(dday_text)
        days_left = int(dm.group(1)) if dm else (0 if "day" in dday_text.lower() else None)

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
                type_hint=type_hint,
                channels_raw=channels,
            )
        )
    return campaigns


class SeouloubaConnector(Connector):
    key = "seoulouba"
    label = "서울오빠"
    base_url = BASE_URL
    # "촬영"은 채널 아이콘 자리에 오는 기자단 표시라 채널로 보지 않는다 (유형 쪽에서 기자단으로 잡힘)
    type_hints = {"촬영기자단": "기자단", "기자단": "기자단"}
    channel_hints = {"네이버블로그": "blog", "인스타그램": "instagram", "유튜브": "youtube", "릴스": "reels"}

    def fetch(self) -> list[RawCampaign]:
        campaigns: list[RawCampaign] = []
        session = requests.Session()
        session.headers.update(HEADERS)
        for cat, category_type in CATEGORIES.items():
            resp = get_with_retry(session, LIST_URL, params={"cat": cat})
            found = parse_list(resp.text, category_type)
            print(f"[서울오빠] cat={cat}({category_type}): {len(found)}건")
            campaigns += found
            time.sleep(2)
        return campaigns


if __name__ == "__main__":
    items = SeouloubaConnector().fetch()
    print(f"수집된 캠페인: {len(items)}개")
    for c in items[:5]:
        print(c)
