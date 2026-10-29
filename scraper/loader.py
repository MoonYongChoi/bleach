"""정제된(normalize.py) 캠페인 레코드를 Supabase(Postgres) campaigns 테이블에 upsert."""

from __future__ import annotations

import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.local"))

UPSERT_SQL = """
insert into public.campaigns
    (platform, title, region_sido, region_gugun, deadline_date, announce_date, source_url, category,
     category_raw, campaign_type, review_channels, description, image_url, vendor, recruit_count,
     applicant_count, is_active)
values
    (%(platform)s, %(title)s, %(region_sido)s, %(region_gugun)s, %(deadline_date)s,
     %(announce_date)s, %(source_url)s, %(category)s, %(category_raw)s, %(campaign_type)s,
     %(review_channels)s, %(description)s, %(image_url)s, %(vendor)s, %(recruit_count)s, %(applicant_count)s,
     %(is_active)s)
on conflict (source_url) do update set
    title = excluded.title,
    region_sido = excluded.region_sido,
    region_gugun = excluded.region_gugun,
    deadline_date = excluded.deadline_date,
    announce_date = excluded.announce_date,
    category = excluded.category,
    category_raw = excluded.category_raw,
    campaign_type = excluded.campaign_type,
    review_channels = excluded.review_channels,
    description = excluded.description,
    image_url = excluded.image_url,
    vendor = excluded.vendor,
    recruit_count = excluded.recruit_count,
    applicant_count = excluded.applicant_count,
    is_active = excluded.is_active;
"""

# 이번 수집에서 다시 보이지 않았더라도 마감일이 지난 건 내린다 (KST 기준 오늘 이전).
EXPIRE_SQL = """
update public.campaigns
set is_active = false
where is_active
  and deadline_date < (now() at time zone 'Asia/Seoul')::date;
"""

_DEFAULTS = {
    "category_raw": None,
    "campaign_type": None,
    "review_channels": [],
    "is_active": True,
    "description": None,
    "image_url": None,
    "vendor": None,
    "recruit_count": None,
    "applicant_count": None,
}

_COLUMNS = {
    "platform", "title", "region_sido", "region_gugun", "deadline_date", "announce_date",
    "source_url", "category", "category_raw", "campaign_type", "review_channels", "description", "image_url",
    "vendor", "recruit_count", "applicant_count", "is_active",
}


def upsert_campaigns(campaigns: list[dict]) -> tuple[int, int]:
    """(upsert 건수, 마감 지나 비활성화된 건수)."""
    rows = [
        {**_DEFAULTS, **{k: v for k, v in c.items() if k in _COLUMNS}}
        for c in campaigns
        if c.get("source_url") and c.get("title")
    ]

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn, conn.cursor() as cur:
            if rows:
                psycopg2.extras.execute_batch(cur, UPSERT_SQL, rows, page_size=100)
            cur.execute(EXPIRE_SQL)
            expired = cur.rowcount
        return len(rows), expired
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
    n, expired = upsert_campaigns(sample)
    print(f"upsert {n}건 완료, 비활성화 {expired}건")
