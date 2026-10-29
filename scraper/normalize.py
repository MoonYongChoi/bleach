"""플랫폼별 스크래퍼 결과를 BLEACH 표준 레코드로 정제한다.

스크래퍼(revu/pavlovu/reviewnote)는 사이트에서 읽은 값을 거의 그대로 넘기고, 여기서
제목/마감일/모집·신청인원/이미지/분류/지역을 한 가지 규칙으로 맞춘다. 그래서 플랫폼이
늘어나도 "BLEACH에 들어가는 데이터가 어떤 모양인지"는 이 파일 하나만 보면 된다.

스크래퍼가 표준 필드 외에 넘길 수 있는 힌트 키 (DB에는 저장되지 않음):
- region_raw: 원본 지역 텍스트 — region_sido/region_gugun이 비어 있으면 이걸로 해석한다.
- type_hint: 원본 유형 텍스트 (예: 리뷰노트 sort "VISIT", 레뷰 페이지 "지역") — campaign_type 판정용.
- deadline_days_left: 정확한 날짜가 없을 때 쓰는 "D-N"의 N.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from regions import is_non_geo, normalize_sido, resolve_region

KST = ZoneInfo("Asia/Seoul")

# src/lib/categories.ts 의 CATEGORIES 라벨과 같은 순서/표기를 유지할 것.
STANDARD_CATEGORIES = ["맛집", "카페·디저트", "뷰티", "여행·숙박", "식품·배송", "디지털", "생활", "문화·여가"]

# 플랫폼 원본 카테고리 -> 표준 라벨. 여기 없는 값과 GENERIC_RAW_CATEGORIES는 키워드로 추론한다.
CATEGORY_ALIASES = {
    "맛집": "맛집", "음식점": "맛집", "배달": "맛집", "테이크아웃": "맛집",
    "카페": "카페·디저트", "디저트": "카페·디저트", "카페/디저트": "카페·디저트",
    "뷰티": "뷰티", "패션": "뷰티", "헤어": "뷰티", "미용": "뷰티",
    "여행": "여행·숙박", "숙박": "여행·숙박", "여행/숙박": "여행·숙박",
    "식품": "식품·배송",
    "디지털": "디지털", "가전": "디지털", "IT": "디지털",
    "생활": "생활", "서비스": "생활", "반려동물": "생활", "유아동": "생활", "리빙": "생활",
    "문화": "문화·여가", "여가": "문화·여가", "운동": "문화·여가", "도서": "문화·여가",
    "문화/여가": "문화·여가", "체험": "문화·여가",
}

# 카테고리처럼 생겼지만 실제로는 유형/페이지 이름이라 분류 정보가 없는 값
GENERIC_RAW_CATEGORIES = {"기타", "제품", "지역", "배송", "방문", "출장", "기자단", "전체", "구매평"}

# 제목+제공내역 키워드 -> 표준 라벨. 같은 점수면 이 dict 순서가 우선순위.
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "카페·디저트": (
        "카페", "커피", "디저트", "베이커리", "빵", "케이크", "케익", "마카롱", "브런치",
        "젤라또", "도넛", "쿠키", "티룸", "와플", "빙수", "크로플",
    ),
    "맛집": (
        "장어", "오징어", "바베큐", "비스트로", "혼술바", "안주", "노미호다이", "주류", "식사", "타코",
        "맛집", "식당", "레스토랑", "다이닝", "고기", "삼겹", "갈비", "한우", "곱창", "막창",
        "족발", "보쌈", "초밥", "스시", "오마카세", "횟집", "물회", "생선회", "회센터", "파스타", "피자", "치킨",
        "국밥", "냉면", "칼국수", "떡볶이", "분식", "라멘", "쌀국수", "이자카야", "술집",
        "포차", "주점", "뷔페", "한식", "중식", "일식", "양식", "버거", "닭갈비", "샤브",
        "마라", "훠궈", "돈까스", "우동", "주물럭", "식사권", "인분",
    ),
    "뷰티": (
        "마스카라", "마스크", "살롱", "반영구", "시술", "클리닉", "염색", "브로우", "목걸이", "장갑", "명품",
        "화장품", "스킨", "크림", "세럼", "앰플", "토너", "마스크팩", "선크림", "선스틱",
        "립스틱", "립밤", "립틴트", "쿠션", "클렌징", "샴푸", "트리트먼트", "헤어", "미용실", "네일", "속눈썹",
        "왁싱", "피부", "에스테틱", "피부관리", "메이크업", "향수", "바디", "탈모", "두피",
        "뷰티", "패션", "의류", "주얼리", "액세서리", "가방", "신발", "마사지기",
    ),
    "여행·숙박": (
        "1박", "가옥", "한옥",
        "호텔", "펜션", "리조트", "숙박", "글램핑", "캠핑", "풀빌라", "게스트하우스",
        "스테이", "숙소", "여행", "투어", "모텔", "객실",
    ),
    "식품·배송": (
        "와인", "소비뇽", "맥주",
        "과자", "크런치", "먹거리", "연어",
        "식품", "간식", "샐러드", "밀키트", "도시락", "음료", "주스", "즙", "건강식품",
        "영양제", "비타민", "유산균", "단백질", "프로틴", "김치", "반찬", "과일", "쌀",
        "소스", "견과", "젤리", "티백", "닭가슴살", "1팩", "2팩", "3팩", "1박스",
    ),
    "디지털": (
        "전자랜드", "전자", "휴대폰", "인터넷", "TV", "베스트샵",
        "이어폰", "헤드폰", "충전기", "보조배터리", "스마트", "노트북", "키보드", "마우스",
        "모니터", "가전", "청소기", "공기청정기", "블루투스", "카메라", "태블릿", "케이스",
        "스피커", "앱 ", "어플",
    ),
    "문화·여가": (
        "피티", "콘서트",
        "심레이싱", "테니스", "레슨", "댄스", "스튜디오", "사주", "궁합", "신점", "소개팅", "자유이용권", "체형",
        "공연", "전시", "박람회", "페어", "뮤지컬", "영화", "클래스", "원데이", "공방",
        "방탈출", "볼링", "골프", "필라테스", "요가", "헬스", "PT", "수영", "도서", "책",
        "키즈카페", "파티", "입장권", "티켓", "체험권", "축제", "푸드위크",
    ),
    "생활": (
        "사료", "탈취제", "보호대", "다이어리", "깔창", "키링", "자동차", "검사소", "공업사", "도색", "재무", "컨설팅",
        "청소", "세제", "수납", "주방", "생활용품", "반려", "강아지", "고양이", "펫",
        "유아", "아기", "베이비", "육아", "인테리어", "가구", "매트리스", "침구", "이사",
        "세차", "렌탈", "꽃", "텀블러", "학원", "병원", "치과", "한의원",
    ),
}

CAMPAIGN_TYPES = ("방문", "배송", "기자단", "재택", "기타")
TYPE_HINTS = {
    # 리뷰노트 sort
    "VISIT": "방문", "DELIVERY": "배송", "PURCHASE": "배송", "REPORTER": "기자단", "PRESS": "기자단",
    # 레뷰 카테고리 페이지 / 파블로 카테고리·지역 칸
    "지역": "방문", "방문": "방문", "출장": "방문",
    "제품": "배송", "배송": "배송", "구매평": "배송", "구매": "배송",
    "방문자": "방문",
    "기자단": "기자단",
    "재택": "재택",  # 리뷰노트는 재택 캠페인의 city/sido 칸에 "재택"을 넣어 보낸다
}

_PLACEHOLDER_IMAGE_RE = re.compile(r"(blank|noimage|no_image|placeholder|spacer|default)\.(gif|png|jpe?g|svg)", re.I)
_WS_RE = re.compile(r"\s+")
# 파블로 기자단 카드는 <strong>에 캠페인명이 아니라 보상("5,000포인트")이 들어 있다.
_REWARD_ONLY_TITLE_RE = re.compile(r"^[\d,]+\s*(포인트|P|원)$")
# 상세페이지에서 "제공내역" 다음 줄로 잘못 잡히는 섹션 제목들
_JUNK_DESCRIPTIONS = {"추가 안내사항", "안내사항", "상세 안내", "상세페이지 참고"}
_BRACKET_PREFIX_RE = re.compile(r"^\s*[\[【(]([^\]】)]{1,20})[\]】)]\s*")


def today_kst() -> date:
    """스크래퍼는 UTC로 도는 GitHub Actions에서도 실행되므로 '오늘'은 항상 KST 기준."""
    return datetime.now(KST).date()


@dataclass
class NormalizeResult:
    record: Optional[dict]  # None이면 적재하지 않음 (필수값 누락)
    issues: list[str] = field(default_factory=list)


def clean_text(value) -> Optional[str]:
    if value is None:
        return None
    text = _WS_RE.sub(" ", str(value)).strip()
    return text or None


def clean_title(value) -> Optional[str]:
    title = clean_text(value)
    if not title:
        return None
    # 남아 있는 "[지역]"/"[업체]" 프리픽스는 다른 필드로 이미 분리됐으므로 제목에서 뗀다.
    m = _BRACKET_PREFIX_RE.match(title)
    if m and title[m.end():].strip():
        title = title[m.end():].strip()
    return title


def clean_count(value) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        digits = value.replace(",", "").strip()
        if not digits.isdigit():
            return None
        value = int(digits)
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def clean_image_url(value) -> Optional[str]:
    url = clean_text(value)
    if not url:
        return None
    if url.startswith("//"):
        url = "https:" + url
    if not url.startswith(("http://", "https://")):
        return None
    if _PLACEHOLDER_IMAGE_RE.search(url):
        return None
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]  # 배포 사이트가 https라 mixed content 방지
    return url


def to_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(KST)
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if dt.tzinfo is not None:
            dt = dt.astimezone(KST)  # "2026-11-13T14:59:59Z" == 11/13 23:59 KST
        return dt.date()
    return None


def infer_campaign_type(raw: dict) -> str:
    for key in ("type_hint", "category_raw", "category", "region_raw", "region_sido", "region_gugun"):
        hint = raw.get(key)
        if isinstance(hint, str) and hint.strip() in TYPE_HINTS:
            return TYPE_HINTS[hint.strip()]
    if (raw.get("region_sido") and not is_non_geo(raw["region_sido"])) or raw.get("region_raw"):
        return "방문"
    return "기타"


def _keyword_category(text: str) -> Optional[str]:
    scores: dict[str, int] = {}
    for label, keywords in CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits:
            scores[label] = hits
    if not scores:
        return None
    best = max(scores.values())
    return next(label for label in CATEGORY_KEYWORDS if scores.get(label) == best)


def normalize_category(raw_category: Optional[str], title: str, description: Optional[str], campaign_type: str) -> Optional[str]:
    raw = clean_text(raw_category)
    text = f" {title} {description or ''} "
    inferred = _keyword_category(text)

    mapped = None
    if raw and raw not in GENERIC_RAW_CATEGORIES:
        mapped = CATEGORY_ALIASES.get(raw) or (raw if raw in STANDARD_CATEGORIES else None)

    category = mapped or inferred
    # 플랫폼이 "맛집"으로 묶어 두는 카페/디저트는 더 구체적인 쪽으로 보정
    if mapped == "맛집" and inferred == "카페·디저트":
        category = inferred

    # 같은 음식이라도 방문형이면 맛집, 배송형이면 식품
    if campaign_type == "배송" and category in ("맛집", "카페·디저트"):
        category = "식품·배송"
    elif campaign_type == "방문" and category == "식품·배송":
        category = "맛집"
    return category


def normalize_campaign(raw: dict, today: Optional[date] = None) -> NormalizeResult:
    today = today or today_kst()
    issues: list[str] = []

    source_url = clean_text(raw.get("source_url"))
    title = clean_title(raw.get("title"))
    platform = clean_text(raw.get("platform"))
    if not source_url or not title or not platform:
        return NormalizeResult(None, ["missing_required"])

    description = clean_text(raw.get("description"))
    if description == title or description in _JUNK_DESCRIPTIONS:
        description = None
    vendor = clean_text(raw.get("vendor"))

    # 마감일
    deadline = to_date(raw.get("deadline_date"))
    if deadline is None and raw.get("deadline_days_left") is not None:
        days_left = clean_count(raw.get("deadline_days_left"))
        if days_left is not None:
            deadline = today + timedelta(days=days_left)
    if deadline and deadline > today + timedelta(days=365):
        issues.append("deadline_too_far")
        deadline = None
    is_active = not (deadline and deadline < today)
    if not is_active:
        issues.append("expired")
    if _REWARD_ONLY_TITLE_RE.match(title):
        # 무엇을 하는 캠페인인지 알 수 없는 카드라 노출하지 않는다 (스크래퍼 셀렉터 수정 필요).
        issues.append("title_is_reward")
        is_active = False
    if deadline is None:
        issues.append("no_deadline")

    # 모집/신청 인원
    recruit = clean_count(raw.get("recruit_count"))
    applicant = clean_count(raw.get("applicant_count"))
    if recruit == 0:
        recruit = None
    if recruit is None:
        issues.append("no_recruit_count")
    if applicant is None:
        issues.append("no_applicant_count")

    # 이미지
    image_url = clean_image_url(raw.get("image_url"))
    if image_url is None:
        issues.append("no_image")

    # 유형 / 지역
    campaign_type = infer_campaign_type(raw)
    raw_sido = None if is_non_geo(raw.get("region_sido")) else raw.get("region_sido")
    region_sido = normalize_sido(raw_sido)
    region_gugun = clean_text(raw.get("region_gugun"))
    if is_non_geo(region_gugun):
        region_gugun = None
    if raw_sido and not region_sido:
        # 시/도 칸에 시/도가 아닌 값이 왔으면 원본 텍스트로 다시 해석
        region_sido, region_gugun = resolve_region(f"{raw_sido} {region_gugun or ''}")
    if not region_sido and not region_gugun:
        region_sido, region_gugun = resolve_region(raw.get("region_raw"))
    elif region_gugun and not region_sido:
        region_sido, region_gugun = resolve_region(region_gugun)
    if is_non_geo(region_gugun):
        region_gugun = None
    if campaign_type in ("배송", "재택"):
        region_sido = region_gugun = None  # 전국 대상 — 지역 필터에 섞이지 않게
    elif campaign_type == "방문" and not region_sido:
        issues.append("region_unresolved")

    # 분류
    category_raw = clean_text(raw.get("category_raw", raw.get("category")))
    category = normalize_category(category_raw, title, description, campaign_type)
    if category is None:
        issues.append("category_unresolved")

    record = {
        "platform": platform,
        "title": title,
        "region_sido": region_sido,
        "region_gugun": region_gugun,
        "deadline_date": deadline,
        "announce_date": to_date(raw.get("announce_date")),
        "source_url": source_url,
        "category": category,
        "category_raw": category_raw,
        "campaign_type": campaign_type,
        "description": description,
        "image_url": image_url,
        "vendor": vendor,
        "recruit_count": recruit,
        "applicant_count": applicant,
        "is_active": is_active,
    }
    return NormalizeResult(record, issues)


def normalize_all(raws: list[dict], today: Optional[date] = None) -> tuple[list[dict], list[tuple[dict, list[str]]]]:
    """(적재할 레코드, [(레코드 또는 원본, issues)]) — source_url 중복은 뒤에 온 값으로 덮는다."""
    by_url: dict[str, dict] = {}
    report: list[tuple[dict, list[str]]] = []
    for raw in raws:
        result = normalize_campaign(raw, today)
        report.append((result.record or raw, result.issues))
        if result.record:
            by_url[result.record["source_url"]] = result.record
    return list(by_url.values()), report
