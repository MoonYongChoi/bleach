"""이미 적재된 행을 현재 normalize.py 규칙으로 다시 정제한다.

정제 규칙을 바꾼 뒤, 다음 스크래핑에서 다시 수집되지 않는 예전 행까지 맞추고 싶을 때 쓴다.

    python backfill.py            # 바뀔 내용만 요약 출력 (DB 안 건드림)
    python backfill.py --apply    # 실제로 UPDATE
"""

from __future__ import annotations

import argparse
import os
from collections import Counter

from connectors import BY_LABEL
from normalize import normalize_for

UPDATED_COLUMNS = (
    "title", "region_sido", "region_gugun", "category", "category_raw", "campaign_type",
    "review_channels", "description", "image_url", "recruit_count", "applicant_count", "is_active",
)


def plan(rows: list[dict]) -> tuple[list[dict], Counter]:
    """(바뀌는 행들의 새 값 [{id, ...}], 컬럼별 변경 건수)."""
    changes: list[dict] = []
    changed_cols: Counter = Counter()
    for row in rows:
        connector = BY_LABEL.get(row["platform"])
        if connector is None:
            continue  # 등록되지 않은 플랫폼(테스트 행 등)은 건드리지 않음
        # 플랫폼별로 예전 스키마 흔적을 되돌리는 건 각 커넥터의 from_db_row 몫
        record = normalize_for(connector, connector.from_db_row(row)).record
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
    review_channels = %(review_channels)s,
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
