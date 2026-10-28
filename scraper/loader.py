"""스크래핑 결과를 Supabase(Postgres) campaigns 테이블에 upsert."""

from __future__ import annotations

import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.local"))

UPSERT_SQL = """
insert into public.campaigns
    (platform, title, region_sido, region_gugun, deadline_date, announce_date, source_url, category,
     description, image_url, vendor, recruit_count, applicant_count)
values
    (%(platform)s, %(title)s, %(region_sido)s, %(region_gugun)s, %(deadline_date)s,
     %(announce_date)s, %(source_url)s, %(category)s, %(description)s, %(image_url)s,
     %(vendor)s, %(recruit_count)s, %(applicant_count)s)
on conflict (source_url) do update set
    title = excluded.title,
    region_sido = excluded.region_sido,
    region_gugun = excluded.region_gugun,
    deadline_date = excluded.deadline_date,
    announce_date = excluded.announce_date,
    category = excluded.category,
    description = excluded.description,
    image_url = excluded.image_url,
    vendor = excluded.vendor,
    recruit_count = excluded.recruit_count,
    applicant_count = excluded.applicant_count,
    is_active = true;
"""

_DEFAULTS = {
    "description": None,
    "image_url": None,
    "vendor": None,
    "recruit_count": None,
    "applicant_count": None,
}


def upsert_campaigns(campaigns: list[dict]) -> int:
    rows = [
        {**_DEFAULTS, **c}
        for c in campaigns
        if c.get("source_url") and c.get("title")
    ]
    if not rows:
        return 0

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn, conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, UPSERT_SQL, rows, page_size=100)
        return len(rows)
    finally:
        conn.close()


if __name__ == "__main__":
    sample = [
        {
            "platform": "테스트",
            "title": "로더 연결 테스트",
            "region_sido": None,
            "region_gugun": None,
            "deadline_date": None,
            "announce_date": None,
            "source_url": "https://example.com/test-loader",
            "category": None,
        }
    ]
    n = upsert_campaigns(sample)
    print(f"upsert {n}건 완료")
