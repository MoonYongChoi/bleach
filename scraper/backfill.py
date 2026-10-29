"""이미 적재된 행을 현재 normalize.py 규칙으로 다시 정제한다.

정제 규칙을 바꾼 뒤, 다음 스크래핑에서 다시 수집되지 않는 예전 행까지 맞추고 싶을 때 쓴다.

    python backfill.py            # 바뀔 내용만 요약 출력 (DB 안 건드림)
    python backfill.py --apply    # 실제로 UPDATE
"""

from __future__ import annotations

import argparse
import os
from collections import Counter

from normalize import normalize_campaign

UPDATED_COLUMNS = (
    "title", "region_sido", "region_gugun", "category", "category_raw", "campaign_type",
    "description", "image_url", "recruit_count", "applicant_count", "is_active",
)

# 정제 전 스키마에서 category 칸에 들어가던 레뷰 페이지 이름
_REVU_PAGES = {"제품", "지역"}


def row_to_raw(row: dict) -> dict:
    """DB 행 -> 스크래퍼가 넘겼을 법한 원본 dict (normalize 입력 형태)."""
    platform = row["platform"]
    category_raw = row.get("category_raw") or row.get("category")
    raw = {
        "platform": platform,
        "title": row["title"],
        "deadline_date": row.get("deadline_date"),
        "source_url": row["source_url"],
        "description": row.get("description"),
        "image_url": row.get("image_url"),
        "vendor": row.get("vendor"),
        "recruit_count": row.get("recruit_count"),
        "applicant_count": row.get("applicant_count"),
        "category_raw": category_raw,
    }

    if platform == "리뷰노트":
        # 예전 스크래퍼는 제목 뒤에 " - 제공내역"을 붙여 저장했다.
        desc = row.get("description")
        if desc and raw["title"].endswith(f" - {desc}") and len(raw["title"]) > len(desc) + 3:
            raw["title"] = raw["title"][: -(len(desc) + 3)]
        raw["region_sido"] = row.get("region_sido")
        raw["region_gugun"] = row.get("region_gugun")
    elif platform == "레뷰":
        if category_raw in _REVU_PAGES:
            raw["type_hint"] = category_raw
            raw["category_raw"] = None
        raw["region_raw"] = row.get("region_gugun") or row.get("region_sido")
    else:
        # 파블로: 예전 resolve_region 결과(gugun=원본 텍스트)로 원본 지역을 복원해 다시 해석
        raw["region_raw"] = row.get("region_gugun") or row.get("region_sido")

    if row.get("campaign_type") and "type_hint" not in raw:
        raw["type_hint"] = row["campaign_type"]
    return raw


def plan(rows: list[dict]) -> tuple[list[dict], Counter]:
    """(바뀌는 행들의 새 값 [{id, ...}], 컬럼별 변경 건수)."""
    changes: list[dict] = []
    changed_cols: Counter = Counter()
    for row in rows:
        record = normalize_campaign(row_to_raw(row)).record
        if record is None:
            continue
        diff = {c: record[c] for c in UPDATED_COLUMNS if record[c] != row.get(c)}
        if diff:
            changed_cols.update(diff.keys())
            changes.append({"id": row["id"], **{c: record[c] for c in UPDATED_COLUMNS}})
    return changes, changed_cols


UPDATE_SQL = """
update public.campaigns set
    title = %(title)s, region_sido = %(region_sido)s, region_gugun = %(region_gugun)s,
    category = %(category)s, category_raw = %(category_raw)s, campaign_type = %(campaign_type)s,
    description = %(description)s, image_url = %(image_url)s, recruit_count = %(recruit_count)s,
    applicant_count = %(applicant_count)s, is_active = %(is_active)s
where id = %(id)s
"""


def main() -> None:
    import psycopg2
    import psycopg2.extras
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.local"))
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("select * from public.campaigns")
            changes, changed_cols = plan(cur.fetchall())
            print(f"변경 대상 {len(changes)}행 — 컬럼별: {dict(changed_cols)}")
            if args.apply and changes:
                psycopg2.extras.execute_batch(cur, UPDATE_SQL, changes, page_size=100)
                print("적용 완료")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
