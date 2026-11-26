"""정제된(normalize.py) 캠페인 레코드를 Supabase(Postgres) campaigns 테이블에 upsert."""

from __future__ import annotations

import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.local"))

UPSERT_SQL = """
insert into public.campaigns
    (platform, title, region_sido, region_gugun, region_guguns, deadline_date, announce_date, source_url, category,
     category_raw, campaign_type, review_channels, description, image_url, vendor, recruit_count,
     applicant_count, is_active)
values
    (%(platform)s, %(title)s, %(region_sido)s, %(region_gugun)s, %(region_guguns)s, %(deadline_date)s,
     %(announce_date)s, %(source_url)s, %(category)s, %(category_raw)s, %(campaign_type)s,
     %(review_channels)s, %(description)s, %(image_url)s, %(vendor)s, %(recruit_count)s, %(applicant_count)s,
     %(is_active)s)
on conflict (source_url) do update set
    title = excluded.title,
    region_sido = excluded.region_sido,
    region_gugun = excluded.region_gugun,
    region_guguns = excluded.region_guguns,
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
    is_active = excluded.is_active,
    last_seen_at = now();
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
    "region_guguns": [],
    "is_active": True,
    "description": None,
    "image_url": None,
    "vendor": None,
    "recruit_count": None,
    "applicant_count": None,
}

_COLUMNS = {
    "platform", "title", "region_sido", "region_gugun", "region_guguns", "deadline_date", "announce_date",
    "source_url", "category", "category_raw", "campaign_type", "review_channels", "description", "image_url",
    "vendor", "recruit_count", "applicant_count", "is_active",
}


# 한 트랜잭션 안에서 now()는 같으므로, 이번에 처음 들어온 행은 created_at = now()인 행이다.
NEW_COUNT_SQL = "select platform, count(*) from public.campaigns where created_at = now() group by platform"

RUN_SQL = """
insert into public.scrape_runs (run_id, platform, started_at, finished_at, status, fetched, saved, new_count,
                                closed_count, error)
values (%(run_id)s, %(platform)s, %(started_at)s, %(finished_at)s, %(status)s, %(fetched)s, %(saved)s,
        %(new_count)s, %(closed_count)s, %(error)s)
"""

# 목록을 끝까지 읽은 플랫폼에서, 이번 회차에 안 보인 모집 중 캠페인 = 모집이 끝났거나 내려간 캠페인.
# upsert가 같은 트랜잭션에서 last_seen_at = now()로 바꾸므로, 이번에 본 행은 now()보다 작지 않다.
UNSEEN_COUNT_SQL = """
select count(*) from public.campaigns where platform = %s and is_active and last_seen_at < now()
"""
CLOSE_UNSEEN_SQL = """
update public.campaigns set is_active = false
where platform = %s and is_active and last_seen_at < now()
"""
# 사이트 목록에 "마감"으로 나온 캠페인: 모집 중으로 남아 있으면 내리고, 앞당겨진 실제 마감일로 고친다.
# 새로 넣지는 않는다 (이미 끝난 캠페인을 목록에 들일 이유가 없다).
CLOSE_LISTED_SQL = """
update public.campaigns c
set is_active = false,
    deadline_date = (v.ended_at::timestamptz at time zone 'Asia/Seoul')::date,
    updated_at = now()
from (values %s) as v(source_url, ended_at)
where c.source_url = v.source_url and c.is_active
"""


def close_listed(cur, platform: str, listed: dict[str, str]) -> int:
    if not listed:
        return 0
    # 한 문장으로 보낸다 — 여러 묶음으로 나누면 rowcount가 마지막 묶음 것만 남는다
    psycopg2.extras.execute_values(cur, CLOSE_LISTED_SQL, list(listed.items()), page_size=len(listed))
    n = cur.rowcount
    if n:
        print(f"[{platform}] 사이트에 마감으로 나온 캠페인 {n}건 모집 종료 처리")
    return n


# 한 번에 이 비율보다 많이 사라지면 사이트 구조가 바뀌었거나 덜 읽은 것일 수 있어 내리지 않는다
MAX_CLOSE_RATIO = 0.5


def close_unseen(cur, platform: str, saved: int) -> int:
    """목록에서 사라진 캠페인을 내리고 그 수를 돌려준다. 너무 많으면 건너뛰고 0."""
    cur.execute(UNSEEN_COUNT_SQL, (platform,))
    unseen = cur.fetchone()[0]
    if unseen == 0:
        return 0
    if unseen > MAX_CLOSE_RATIO * (unseen + saved):
        print(f"[{platform}] 목록에서 사라진 캠페인 {unseen}건 — 이번에 본 {saved}건에 비해 너무 많아 내리지 않음 (확인 필요)")
        return 0
    cur.execute(CLOSE_UNSEEN_SQL, (platform,))
    print(f"[{platform}] 목록에서 사라진 캠페인 {cur.rowcount}건 모집 종료 처리")
    return cur.rowcount


def upsert_campaigns(campaigns: list[dict], runs: list[dict] | None = None) -> tuple[int, int]:
    """(upsert 건수, 마감 지나 비활성화된 건수).

    runs를 주면 플랫폼별 수집 기록(scrape_runs)도 같은 트랜잭션에 남긴다 (/admin 페이지에서 본다).
    각 항목: run_id, platform, started_at, finished_at, status, fetched, error. saved·new_count는 여기서 채운다.
    """
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
            if runs:
                cur.execute(NEW_COUNT_SQL)
                new_by_platform = dict(cur.fetchall())
                saved_by_platform: dict[str, int] = {}
                for r in rows:
                    saved_by_platform[r["platform"]] = saved_by_platform.get(r["platform"], 0) + 1
                closed_by_platform = {
                    r["platform"]: close_unseen(cur, r["platform"], saved_by_platform.get(r["platform"], 0))
                    for r in runs
                    if r.get("status") == "ok" and r.get("complete") and saved_by_platform.get(r["platform"])
                }
                for r in runs:
                    if r.get("status") == "ok" and r.get("closed_listed"):
                        n_closed = close_listed(cur, r["platform"], r["closed_listed"])
                        closed_by_platform[r["platform"]] = closed_by_platform.get(r["platform"], 0) + n_closed
                psycopg2.extras.execute_batch(cur, RUN_SQL, [
                    {
                        **r,
                        "saved": saved_by_platform.get(r["platform"], 0),
                        "new_count": new_by_platform.get(r["platform"], 0),
                        "closed_count": closed_by_platform.get(r["platform"], 0),
                        "error": (r.get("error") or None) and str(r["error"])[:300],
                    }
                    for r in runs
                ])
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


THUMB_SCHEMA_SQL = """
create table if not exists public.thumb_cache (
  url text primary key,
  content_type text not null,
  bytes bytea not null,
  fetched_at timestamptz not null default now()
);
alter table public.thumb_cache enable row level security;
do $$ begin
  if not exists (select 1 from pg_policies where tablename = 'thumb_cache' and policyname = 'thumb_cache is readable') then
    create policy "thumb_cache is readable" on public.thumb_cache for select using (true);
  end if;
end $$;
grant select on public.thumb_cache to anon, authenticated;
"""

THUMB_UPSERT_SQL = """
insert into public.thumb_cache (url, content_type, bytes, fetched_at) values (%s, %s, %s, now())
on conflict (url) do update set content_type = excluded.content_type, bytes = excluded.bytes, fetched_at = now()
"""

# 모집 중 캠페인이 더 이상 쓰지 않고 2주 지난 썸네일은 지운다
THUMB_PRUNE_SQL = """
delete from public.thumb_cache t
where t.fetched_at < now() - interval '14 days'
  and not exists (select 1 from public.campaigns c where c.is_active and c.image_url = t.url)
"""


def save_thumbs(thumbs: dict[str, tuple[str, bytes]]) -> int:
    """수집기가 받아 둔 썸네일을 thumb_cache에 넣는다 (사이트의 /api/thumb가 꺼내 보여 준다)."""
    if not thumbs:
        return 0
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn, conn.cursor() as cur:
            cur.execute(THUMB_SCHEMA_SQL)
            psycopg2.extras.execute_batch(
                cur, THUMB_UPSERT_SQL, [(u, t, psycopg2.Binary(b)) for u, (t, b) in thumbs.items()], page_size=50
            )
            cur.execute(THUMB_PRUNE_SQL)
        return len(thumbs)
    finally:
        conn.close()
