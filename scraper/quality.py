"""데이터 품질 리포트 — 플랫폼별로 핵심 필드가 얼마나 채워졌는지/이상값이 있는지 본다.

    python quality.py   # Supabase에 이미 적재된 데이터를 점검 (DATABASE_URL 필요)

수집 직후 결과는 `python run_all.py --dry-run`이 같은 형식으로 출력한다.
"""

from __future__ import annotations

import os
from collections import Counter, defaultdict

# 점검 대상 필드: (리포트 라벨, 레코드 키)
FIELDS = [
    ("제목", "title"),
    ("마감일", "deadline_date"),
    ("모집인원", "recruit_count"),
    ("신청인원", "applicant_count"),
    ("이미지", "image_url"),
    ("분류", "category"),
    ("지역", "region_sido"),
]

ISSUE_LABELS = {
    "missing_required": "필수값(제목/URL) 누락 → 적재 제외",
    "title_is_reward": "제목이 보상 금액뿐(예: 5,000포인트) → 비활성",
    "expired": "마감 지남 → 비활성",
    "no_deadline": "마감일 없음(상시모집 표시)",
    "deadline_too_far": "마감일 1년 초과 → 버림",
    "no_recruit_count": "모집인원 없음",
    "no_applicant_count": "신청인원 없음",
    "no_image": "이미지 없음/무효",
    "region_unresolved": "방문형인데 시/도 해석 실패",
    "category_unresolved": "분류 추론 실패",
}


def _pct(n: int, total: int) -> str:
    return f"{(100 * n / total):5.1f}%" if total else "   - "


def _print_coverage(rows_by_platform: dict[str, list[dict]]) -> None:
    header = f"{'플랫폼':<8}{'건수':>6}" + "".join(f"{label:>9}" for label, _ in FIELDS)
    print(header)
    print("-" * len(header) * 2)
    for platform, rows in sorted(rows_by_platform.items()):
        total = len(rows)
        cells = []
        for _, key in FIELDS:
            if key == "region_sido":
                # 배송형/기자단은 지역이 없는 게 정상이므로 방문형만 분모로 본다.
                visit = [r for r in rows if r.get("campaign_type") == "방문"]
                filled = sum(1 for r in visit if r.get(key))
                cells.append(_pct(filled, len(visit)))
            else:
                filled = sum(1 for r in rows if r.get(key) not in (None, ""))
                cells.append(_pct(filled, total))
        print(f"{platform:<8}{total:>6}" + "".join(f"{c:>10}" for c in cells))
    print("(지역 = 방문형 중 시/도가 채워진 비율)")


def print_report(report: list[tuple[dict, list[str]]], examples: int = 3) -> None:
    """normalize_all()의 report를 사람이 읽을 수 있게 출력."""
    rows_by_platform: dict[str, list[dict]] = defaultdict(list)
    issues_by_platform: dict[str, Counter] = defaultdict(Counter)
    samples: dict[tuple[str, str], list[str]] = defaultdict(list)
    breakdown: dict[str, Counter] = defaultdict(Counter)

    for record, issues in report:
        platform = record.get("platform") or "?"
        rows_by_platform[platform].append(record)
        breakdown["분류"][(platform, record.get("category") or "(없음)")] += 1
        breakdown["유형"][(platform, record.get("campaign_type") or "(없음)")] += 1
        for issue in issues:
            issues_by_platform[platform][issue] += 1
            key = (platform, issue)
            if len(samples[key]) < examples:
                samples[key].append(f"{record.get('title')} <{record.get('source_url')}>")

    print("\n=== 필드 채움률 ===")
    _print_coverage(rows_by_platform)

    for name, counter in breakdown.items():
        print(f"\n=== {name} 분포 ===")
        per_platform: dict[str, list[str]] = defaultdict(list)
        for (platform, value), n in counter.most_common():
            per_platform[platform].append(f"{value} {n}")
        for platform, parts in sorted(per_platform.items()):
            print(f"{platform}: " + ", ".join(parts))

    print("\n=== 이슈 ===")
    for platform, counter in sorted(issues_by_platform.items()):
        for issue, n in counter.most_common():
            print(f"[{platform}] {ISSUE_LABELS.get(issue, issue)}: {n}건")
            for s in samples[(platform, issue)]:
                print(f"    예) {s}")


DB_CHECKS = {
    "비활성인데 마감일이 미래": "not is_active and deadline_date >= (now() at time zone 'Asia/Seoul')::date",
    "활성인데 마감일이 지남": "is_active and deadline_date < (now() at time zone 'Asia/Seoul')::date",
    "신청인원 > 0인데 모집인원 없음": "applicant_count > 0 and recruit_count is null",
    "음수 인원": "recruit_count < 0 or applicant_count < 0",
    "표준 외 분류": "category is not null and category not in ("
    "'맛집','카페·디저트','뷰티','여행·숙박','식품·배송','디지털','생활','문화·여가')",
    "시/도 표기 비표준": "region_sido is not null and region_sido not in ("
    "'서울','부산','대구','인천','광주','대전','울산','세종','경기','강원','충북','충남','전북','전남','경북','경남','제주')",
    "이미지 URL이 https 아님": "image_url is not null and image_url not like 'https://%'",
    "제목 앞에 [괄호] 남음": "title ~ '^\\s*\\['",
    "활성인데 제목이 보상 금액뿐": "is_active and title ~ '^[0-9,]+\\s*(포인트|P|원)$'",
    "제목에 제공내역이 붙어 있음": "description is not null and title like '% - ' || description",
}


def audit_db() -> None:
    import psycopg2
    import psycopg2.extras
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.local"))
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("select * from public.campaigns where is_active")
            rows = cur.fetchall()
            rows_by_platform: dict[str, list[dict]] = defaultdict(list)
            for r in rows:
                rows_by_platform[r["platform"]].append(r)
            print(f"=== 활성 캠페인 {len(rows)}건 필드 채움률 ===")
            _print_coverage(rows_by_platform)

            print("\n=== 분류 분포 (활성) ===")
            cur.execute(
                "select platform, coalesce(category, '(없음)') c, count(*) n from public.campaigns "
                "where is_active group by 1, 2 order by 1, 3 desc"
            )
            per_platform: dict[str, list[str]] = defaultdict(list)
            for r in cur.fetchall():
                per_platform[r["platform"]].append(f"{r['c']} {r['n']}")
            for platform, parts in sorted(per_platform.items()):
                print(f"{platform}: " + ", ".join(parts))

            print("\n=== 이상값 점검 (전체 행) ===")
            for label, where in DB_CHECKS.items():
                cur.execute(
                    f"select platform, count(*) n, (array_agg(title))[1:2] ex from public.campaigns "
                    f"where {where} group by 1 order by 1"
                )
                found = cur.fetchall()
                if not found:
                    print(f"OK   {label}")
                for r in found:
                    print(f"FAIL {label} — [{r['platform']}] {r['n']}건, 예) {r['ex']}")
    finally:
        conn.close()


if __name__ == "__main__":
    audit_db()
