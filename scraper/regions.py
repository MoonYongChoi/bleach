"""지역 텍스트 정규화 — 스크래퍼가 긁어온 원본 지역 문자열을 (sido, gugun)으로 분리한다.

파블로/레뷰는 목록 페이지에 "용산/중구", "경남", "배송" 같은 비정형 텍스트만 주기 때문에,
시/군/구 이름 -> 시/도 매핑 테이블로 역추적한다. 리뷰노트는 이미 API가 sido/gugun을 분리해서
주므로 이 모듈을 거치지 않는다.
"""

from __future__ import annotations

import re

# 지역이 아니라 캠페인 유형을 뜻하는 라벨 — 지역 칸에 넣지 않고 campaign_type으로 보낸다.
NON_GEO_LABELS = {"배송", "기자단", "실시간", "누구나", "전국", "재택", "구매평", "구매", "방문자"}

# 시/군/구 이름 -> 시/도 후보 목록 (DB에 이미 쓰이고 있는 짧은 표기와 맞춤).
# "중구", "강서구"처럼 여러 시/도에 동명 구/군이 있어 리스트로 둔다 — 같이 온 다른
# 토큰과 교집합을 구해서 모호함을 없앤다.
GU_SI_TO_SIDO: dict[str, list[str]] = {}


def _register(sido: str, names: list[str]) -> None:
    for name in names:
        GU_SI_TO_SIDO.setdefault(name, []).append(sido)


_register(
    "서울",
    [
        "종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구",
        "성북구", "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구",
        "양천구", "강서구", "구로구", "금천구", "영등포구", "동작구", "관악구",
        "서초구", "강남구", "송파구", "강동구",
    ],
)
_register(
    "경기",
    [
        "수원시", "성남시", "고양시", "용인시", "부천시", "안산시", "안양시",
        "남양주시", "화성시", "평택시", "의정부시", "시흥시", "김포시", "광명시",
        "군포시", "이천시", "양주시", "오산시", "구리시", "안성시", "포천시",
        "의왕시", "하남시", "여주시", "동두천시", "과천시", "가평군", "연천군",
        "파주시", "양평군",
    ],
)
_register("인천", ["중구", "동구", "미추홀구", "연수구", "남동구", "부평구", "계양구", "서구", "강화군", "옹진군", "영종구", "검단구"])
_register("부산", ["중구", "서구", "동구", "영도구", "부산진구", "동래구", "남구", "북구", "해운대구", "사하구", "금정구", "강서구", "연제구", "수영구", "사상구", "기장군"])
_register("대구", ["중구", "동구", "서구", "남구", "북구", "수성구", "달서구", "달성군"])
_register("광주", ["동구", "서구", "남구", "북구", "광산구"])
_register("대전", ["동구", "중구", "서구", "유성구", "대덕구"])
_register("울산", ["중구", "남구", "동구", "북구", "울주군"])
_register("강원", ["춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시", "홍천군", "횡성군", "평창군", "정선군", "철원군", "화천군", "양구군", "인제군", "고성군", "양양군"])
_register("충북", ["청주시", "충주시", "제천시", "보은군", "옥천군", "영동군", "증평군", "진천군", "괴산군", "음성군", "단양군"])
_register("충남", ["천안시", "공주시", "보령시", "아산시", "서산시", "논산시", "계룡시", "당진시", "금산군", "부여군", "서천군", "청양군", "홍성군", "예산군", "태안군"])
_register("전북", ["전주시", "군산시", "익산시", "정읍시", "남원시", "김제시", "완주군", "진안군", "무주군", "장수군", "임실군", "순창군", "고창군", "부안군"])
_register("전남", ["목포시", "여수시", "순천시", "나주시", "광양시", "담양군", "곡성군", "구례군", "고흥군", "보성군", "화순군", "장흥군", "강진군", "해남군", "영암군", "무안군", "함평군", "영광군", "장성군", "완도군", "진도군", "신안군"])
_register("경북", ["포항시", "경주시", "김천시", "안동시", "구미시", "영주시", "영천시", "상주시", "문경시", "경산시", "군위군", "의성군", "청송군", "영양군", "영덕군", "청도군", "고령군", "성주군", "칠곡군", "예천군", "봉화군", "울진군", "울릉군"])
_register("경남", ["창원시", "진주시", "통영시", "사천시", "김해시", "밀양시", "거제시", "양산시", "의령군", "함안군", "창녕군", "고성군", "남해군", "하동군", "산청군", "함양군", "거창군", "합천군"])
_register("제주", ["제주시", "서귀포시"])

SIDO_NAMES = {
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
}

# 해외 방문 체험은 시/도 칸에 "해외", 시/군/구 칸에 나라 이름을 넣는다 (필터에서 해외 > 일본 식으로 고름).
OVERSEAS = "해외"
# 나라·주요 도시 -> 나라. 지역 칸(레뷰 "[일본]" 괄호 등)에 올 때만 쓴다 — 제목의 "홍콩", "하와이"는
# 국내 가게 이름인 경우가 많아서(굿모닝홍콩 전포점, 하와이조개 당산점) 보지 않는다.
OVERSEAS_PLACES: dict[str, str] = {}
for _country, _places in {
    "일본": ["일본", "도쿄", "오사카", "후쿠오카", "교토", "삿포로", "오키나와", "나고야", "요코하마"],
    "베트남": ["베트남", "다낭", "호치민", "하노이", "나트랑", "푸꾸옥"],
    "태국": ["태국", "방콕", "치앙마이", "푸켓", "파타야"],
    "대만": ["대만", "타이베이", "가오슝"],
    "중국": ["중국", "상하이", "베이징", "칭다오"],
    "홍콩·마카오": ["홍콩", "마카오"],
    "싱가포르": ["싱가포르"],
    "필리핀": ["필리핀", "세부", "보라카이", "마닐라"],
    "인도네시아": ["인도네시아", "발리"],
    "말레이시아": ["말레이시아", "코타키나발루", "쿠알라룸푸르"],
    "괌·사이판": ["괌", "사이판"],
    "미국": ["미국", "하와이", "뉴욕", "LA", "로스앤젤레스"],
    "유럽": ["유럽", "프랑스", "파리", "영국", "런던", "이탈리아", "스페인"],
    "해외": ["해외"],
}.items():
    for _place in _places:
        OVERSEAS_PLACES[_place] = _country

# 공식/긴 표기 -> DB에서 쓰는 두 글자 표기
SIDO_ALIASES = {
    "서울특별시": "서울", "서울시": "서울",
    "부산광역시": "부산", "부산시": "부산",
    "대구광역시": "대구", "대구시": "대구",
    "인천광역시": "인천", "인천시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전", "대전시": "대전",
    "울산광역시": "울산", "울산시": "울산",
    "세종특별자치시": "세종", "세종시": "세종",
    "경기도": "경기",
    "강원도": "강원", "강원특별자치도": "강원",
    "충청북도": "충북", "충청남도": "충남",
    "전라북도": "전북", "전북특별자치도": "전북", "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남",
    "제주도": "제주", "제주특별자치도": "제주",
}

# 행정구역명이 아닌 생활권/랜드마크 지명 -> (시/도, 시/군/구).
# 레뷰 "[일산] ...", "[코엑스] ..." 처럼 제목 괄호에 자주 나오는 것 위주.
AREA_ALIASES: dict[str, tuple[str, str]] = {
    "일산": ("경기", "고양시"), "분당": ("경기", "성남시"), "판교": ("경기", "성남시"),
    "동탄": ("경기", "화성시"), "광교": ("경기", "수원시"), "영통": ("경기", "수원시"),
    "평촌": ("경기", "안양시"), "산본": ("경기", "군포시"), "위례": ("경기", "성남시"),
    "송도": ("인천", "연수구"), "청라": ("인천", "서구"), "영종도": ("인천", "중구"),
    "강남역": ("서울", "강남구"), "코엑스": ("서울", "강남구"), "삼성역": ("서울", "강남구"),
    "압구정": ("서울", "강남구"), "신사": ("서울", "강남구"), "청담": ("서울", "강남구"),
    "홍대": ("서울", "마포구"), "연남": ("서울", "마포구"), "합정": ("서울", "마포구"),
    "망원": ("서울", "마포구"), "성수": ("서울", "성동구"), "잠실": ("서울", "송파구"),
    "여의도": ("서울", "영등포구"), "이태원": ("서울", "용산구"), "한남": ("서울", "용산구"),
    "명동": ("서울", "중구"), "을지로": ("서울", "중구"), "건대": ("서울", "광진구"),
    "신촌": ("서울", "서대문구"), "종로": ("서울", "종로구"), "익선동": ("서울", "종로구"),
    "목동": ("서울", "양천구"), "마곡": ("서울", "강서구"),
    "서면": ("부산", "부산진구"), "광안리": ("부산", "수영구"), "센텀": ("부산", "해운대구"),
    "동성로": ("대구", "중구"),
}

# 앞뒤에 붙어 매칭을 방해하는 장식 문자열
_REGION_NOISE = ("점", "역", "근처", "인근")


def normalize_sido(raw: str | None) -> str | None:
    """'서울특별시'/'경기도' 같은 표기를 'SIDO_NAMES'의 두 글자 표기로 맞춘다."""
    if not raw:
        return None
    raw = raw.strip()
    if raw in SIDO_NAMES or raw == OVERSEAS:
        return raw
    return SIDO_ALIASES.get(raw)


def is_non_geo(raw: str | None) -> bool:
    return bool(raw) and raw.strip() in NON_GEO_LABELS


def _canonical_gugun(token: str) -> tuple[str, list[str]] | None:
    """'용산' -> ('용산구', ['서울']). 접미사가 생략된 표기도 받아준다."""
    for candidate in (token, f"{token}구", f"{token}시", f"{token}군"):
        sidos = GU_SI_TO_SIDO.get(candidate)
        if sidos:
            return candidate, sidos
    return None


def resolve_region(raw: str | None) -> tuple[str | None, str | None]:
    """원본 지역 텍스트 -> (region_sido, region_gugun).

    해석에 성공하면 gugun은 '용산구', '수원시'처럼 표준 표기로 돌려주고(여러 개면 '/'로 연결),
    해석이 안 되면 원본 텍스트를 gugun에 남겨서 정보가 사라지지 않게 한다.
    지역이 아닌 라벨('배송', '기자단' 등)은 (None, None)을 돌려준다 — 유형은 campaign_type이 담당.
    """
    if not raw:
        return None, None
    raw = raw.strip()
    if not raw or raw in NON_GEO_LABELS:
        return None, None

    sido = normalize_sido(raw)
    if sido:
        return sido, None

    if raw in AREA_ALIASES:
        return AREA_ALIASES[raw]

    # "일본", "도쿄", "일본/오사카"
    overseas = [OVERSEAS_PLACES[t] for t in re.split(r"[/·,\s]+", raw) if t in OVERSEAS_PLACES]
    if overseas:
        countries = [c for c in dict.fromkeys(overseas) if c != OVERSEAS]
        return OVERSEAS, "/".join(countries) or None

    # "서울 강남구", "용산/중구", "경기 · 수원" 등
    tokens = [t for t in raw.replace("·", " ").replace("/", " ").replace(",", " ").split() if t]
    explicit_sido: str | None = None
    guguns: list[str] = []
    candidate_sets: list[set[str]] = []
    unresolved = False
    for token in tokens:
        s = normalize_sido(token)
        if s:
            # "충남/세종"처럼 시/도가 여러 개 묶여 오면 첫 번째를 대표로 쓴다.
            explicit_sido = explicit_sido or s
            continue
        if token in AREA_ALIASES:
            a_sido, a_gugun = AREA_ALIASES[token]
            guguns.append(a_gugun)
            candidate_sets.append({a_sido})
            continue
        hit = _canonical_gugun(token)
        if not hit:
            stripped = token
            for suffix in _REGION_NOISE:
                if stripped.endswith(suffix) and len(stripped) > len(suffix) + 1:
                    stripped = stripped[: -len(suffix)]
            hit = _canonical_gugun(stripped) if stripped != token else None
        if hit:
            guguns.append(hit[0])
            candidate_sets.append(set(hit[1]))
        else:
            unresolved = True

    gugun = "/".join(dict.fromkeys(guguns)) if guguns and not unresolved else raw
    if explicit_sido:
        return explicit_sido, (gugun if guguns or unresolved else None)

    if candidate_sets:
        # 여러 토큰이 공통으로 속하는 시/도가 있으면 그걸로 모호함을 해소한다.
        intersection = set.intersection(*candidate_sets)
        if len(intersection) == 1:
            return next(iter(intersection)), gugun
        if len(candidate_sets[0]) == 1:
            return next(iter(candidate_sets[0])), gugun

    return None, gugun
