-- 수집 회차 기록: 수집기(scraper/run_all.py)가 회차마다 플랫폼별로 한 줄씩 남긴다. /admin 페이지에서 본다.
create table if not exists public.scrape_runs (
  id bigint generated always as identity primary key,
  run_id uuid not null,                 -- 같은 회차의 플랫폼들을 묶는 값
  platform text not null,
  started_at timestamptz not null,
  finished_at timestamptz not null,
  status text not null check (status in ('ok', 'failed', 'skipped')),
  fetched integer not null default 0,   -- 사이트 목록에서 읽은 건수
  saved integer not null default 0,     -- 정제 후 DB에 쓴 건수
  new_count integer not null default 0, -- 그중 처음 들어온 캠페인
  error text
);
create index if not exists scrape_runs_started_idx on public.scrape_runs (started_at desc);

-- 운영 현황(시각·건수·오류 문구)만 담겨 있어 공개 읽기를 허용한다. 쓰기는 수집기(DB 직접 연결)만.
alter table public.scrape_runs enable row level security;
drop policy if exists "scrape_runs are readable" on public.scrape_runs;
create policy "scrape_runs are readable" on public.scrape_runs for select using (true);

-- 플랫폼별 현재 상태 (활성/전체, 마지막으로 목록에서 확인한 시각, 처음 수집한 시각)
create or replace view public.admin_platform_status with (security_invoker = true) as
select
  platform,
  count(*) filter (where is_active) as active,
  count(*) as total,
  max(last_seen_at) as last_seen_at,
  min(created_at) as first_collected_at
from public.campaigns
group by platform;

-- scrape_runs가 생기기 전의 기록 복원: 한 회차에 들어온 행은 created_at(트랜잭션 시각)이 같다.
-- 새 캠페인이 0건인 회차는 여기에 나타나지 않는다.
create or replace view public.admin_collection_history with (security_invoker = true) as
select created_at as collected_at, platform, count(*) as new_count
from public.campaigns
group by created_at, platform;

grant select on public.scrape_runs, public.admin_platform_status, public.admin_collection_history to anon, authenticated;
