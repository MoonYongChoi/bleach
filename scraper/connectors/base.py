"""커넥터 계약 — 새 체험단 플랫폼은 Connector를 상속한 파일 하나 + connectors/__init__.py 등록 한 줄로 붙는다.

커넥터의 책임은 "사이트에서 읽어서 RawCampaign으로 넘기기"까지다. 표준화(분류/지역/마감일/채널 정규화)는
전부 normalize.py가 하고, 플랫폼마다 다른 *해석*(예: 리뷰노트 sort="VISIT"는 방문형)만 커넥터가
type_hints / channel_hints 로 알려준다.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import ClassVar, Optional, Union


@dataclass
class RawCampaign:
    """스크래퍼 → normalize 사이의 약속. 값은 사이트에서 읽은 그대로 넣는다 (정제는 normalize 몫)."""

    source_url: str
    title: Optional[str]
    description: Optional[str] = None
    vendor: Optional[str] = None
    image_url: Optional[str] = None

    # 지역: 이미 시/도·시군구로 나뉘어 오면 region_sido/region_gugun, 아니면 원본 텍스트를 region_raw에
    region_sido: Optional[str] = None
    region_gugun: Optional[str] = None
    region_raw: Optional[str] = None

    # 마감일: date 또는 ISO 문자열(UTC 포함 가능). 정확한 날짜가 없으면 "D-N"의 N을 deadline_days_left에
    deadline_date: Union[date, str, None] = None
    deadline_days_left: Optional[int] = None
    announce_date: Union[date, str, None] = None

    recruit_count: Union[int, str, None] = None
    applicant_count: Union[int, str, None] = None

    category_raw: Optional[str] = None
    # 캠페인 유형 판정용 원본 값 (예: "VISIT", "제품", "배송") — Connector.type_hints로 해석
    type_hint: Optional[str] = None
    # 리뷰 채널 원본 값들 (예: ["BLOG"], ["인스타", "릴스"]) — normalize가 표준 코드로 바꾼다
    channels_raw: list[str] = field(default_factory=list)
    # 구매 후 환급(페이백)형이면 True
    is_payback: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


_BRACKET_RE = re.compile(r"^\s*\[([^\]]{1,30})\]\s*")
_CHANNEL_WORDS = {"블로그", "릴스", "클립", "쇼츠", "숏츠", "인스타", "인스타그램", "유튜브", "틱톡"}
_TYPE_WORDS = {"방문형", "배송형", "구매형", "기자단", "촬영기자단", "방문", "배송", "구매평", "재택"}
_IGNORE_WORDS = {"프리미엄", "긴급", "마감임박", "신규", "추천", "랜덤픽", "only", "단독"}


def split_title_brackets(title: str) -> tuple[str, dict[str, list[str]]]:
    """'[프리미엄][릴스][에이지투웨니스] 시그니처 세트' -> ('시그니처 세트', {channels, types, regions, others}).

    체험단 사이트들은 제목 앞 괄호에 지역/유형/채널/브랜드를 섞어 넣는다. 지역인지는 regions.resolve_region이
    시/도를 찾는지로 판단하고, 아무것도 아니면 others(보통 업체·브랜드명)로 돌려준다.
    """
    from regions import resolve_region

    found: dict[str, list[str]] = {"channels": [], "types": [], "regions": [], "others": []}
    rest = title or ""
    while True:
        m = _BRACKET_RE.match(rest)
        if not m or not rest[m.end():].strip():
            break
        token = m.group(1).strip()
        rest = rest[m.end():]
        if token in _CHANNEL_WORDS:
            found["channels"].append(token)
        elif token in _TYPE_WORDS:
            found["types"].append(token)
        elif token.lower() in _IGNORE_WORDS:
            pass
        elif resolve_region(token)[0]:
            found["regions"].append(token)
        else:
            found["others"].append(token)
    return rest.strip(), found


def get_with_retry(session, url: str, *, method: str = "GET", tries: int = 3, **kwargs):
    """접속 시간 초과가 간헐적으로 나는 사이트용 (GitHub 러너 IP에 따라 막히는 경우가 있다)."""
    import time

    import requests

    kwargs.setdefault("timeout", 30)
    for attempt in range(1, tries + 1):
        try:
            resp = session.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout):
            if attempt == tries:
                raise
            time.sleep(5 * attempt)


class Connector:
    key: ClassVar[str]  # DB/코드에서 쓰는 불변 키 (예: "revu")
    label: ClassVar[str]  # 화면 표시 + 현재 campaigns.platform 값 (예: "레뷰")
    base_url: ClassVar[str]
    needs_browser: ClassVar[bool] = False  # Playwright 필요 여부 (수집에)
    # 수집은 requests로 되지만 상세 페이지는 JS로 그려져서 검수에는 브라우저가 필요한 경우 (리뷰노트)
    verify_with_browser: ClassVar[bool] = False
    # 브라우저로 열 때 쓸 User-Agent (기본 HeadlessChrome을 막는 사이트용)
    browser_user_agent: ClassVar[Optional[str]] = None
    required_env: ClassVar[tuple[str, ...]] = ()
    # 이 플랫폼 고유의 유형/채널 표기 -> 표준값. 공통 한국어 표기("방문", "배송" 등)는 normalize에 있다.
    type_hints: ClassVar[dict[str, str]] = {}
    channel_hints: ClassVar[dict[str, str]] = {}
    # 사이트가 채널을 따로 표시하지 않을 때의 기본 채널 (예: 레뷰는 블로그가 기본이고 릴스 등만 표시)
    default_channels: ClassVar[tuple[str, ...]] = ()

    def fetch(self) -> list[RawCampaign]:
        raise NotImplementedError

    def prepare_browser(self, context) -> None:
        """needs_browser 커넥터가 페이지를 열기 전에 할 일 (예: 로그인). verify.py도 이걸 쓴다."""

    def from_db_row(self, row: dict) -> RawCampaign:
        """이미 적재된 행 -> RawCampaign (backfill.py가 새 규칙으로 재정제할 때 사용).

        기본 구현은 저장된 값을 그대로 원본처럼 다시 넘긴다. 예전 스키마의 흔적을 되돌려야 하는
        플랫폼만 오버라이드한다.
        """
        # campaign_type이 있으면 이미 정제된 행이다: 시/도·시군구와 category_raw를 그대로 믿는다.
        # 없으면 정제 전 스키마 — category 칸에 원본 분류가, region_gugun에 원본 지역 텍스트가 있다.
        normalized = row.get("campaign_type") is not None
        return RawCampaign(
            source_url=row["source_url"],
            title=row["title"],
            description=row.get("description"),
            vendor=row.get("vendor"),
            image_url=row.get("image_url"),
            region_sido=row.get("region_sido") if normalized else None,
            region_gugun=row.get("region_gugun") if normalized else None,
            region_raw=None if normalized else (row.get("region_gugun") or row.get("region_sido")),
            deadline_date=row.get("deadline_date"),
            announce_date=row.get("announce_date"),
            recruit_count=row.get("recruit_count"),
            applicant_count=row.get("applicant_count"),
            category_raw=row.get("category_raw") if normalized else row.get("category"),
            type_hint=row.get("campaign_type"),
            channels_raw=list(row.get("review_channels") or []),
            is_payback=row.get("campaign_type") == "구매",
        )
