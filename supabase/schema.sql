-- BLEACH: campaigns 테이블 (Day1 — 데이터 표준화 스키마)
-- Supabase 대시보드 > SQL Editor 에서 실행하세요.

create table if not exists public.campaigns (
  id uuid primary key default gen_random_uuid(),

  -- 1. 플랫폼명: 레뷰(revu) / 파블로(pavlovu) / 리뷰노트(reviewnote)
  platform text not null,

  -- 2. 체험단명/제목
  title text not null,

  -- 3. 지역/위치 (예: 서울 / 강남구, 전국(배송)은 region_gugun = null)
  region_sido text,
  region_gugun text,
  -- 하위 지역 필터용: region_gugun을 '/'로 나눈 배열 (시/도가 해석된 경우에만)
  region_guguns text[] not null default '{}',

  -- 4. 일정/마감일
  deadline_date date,
  announce_date date,

  -- 5. 원문 URL (Outlink) — 중복 수집 방지를 위한 unique 키
  source_url text not null unique,

  -- 표준 분류 8종 (scraper/normalize.py STANDARD_CATEGORIES = src/lib/categories.ts 라벨)
  category text,
  -- 플랫폼 원본 분류 텍스트 (디버깅/재분류용)
  category_raw text,
  -- 캠페인 유형: 방문(체험형) / 배송(제품 제공형) / 구매(구매 후 환급형) / 기자단 / 기타
  -- 배송·구매형은 지역 없음
  campaign_type text,
  -- 리뷰 채널 코드 배열: blog / instagram / reels / youtube / shorts / tiktok / clip
  review_channels text[] not null default '{}',

  -- 6. 제공내역(체험단 상세 혜택 설명) / 목록 썸네일
  description text,
  image_url text,

  -- 7. 업체명 / 지원 현황 (지원률 = applicant_count / recruit_count)
  vendor text,
  recruit_count integer,
  applicant_count integer,

  is_active boolean not null default true,
  -- 수집 목록에서 마지막으로 확인된 시각 (loader.py가 upsert할 때만 갱신, 수동 수정에는 안 바뀜)
  last_seen_at timestamptz not null default now(),
  -- 경쟁률(모집 1명당 신청자 수) — DB가 계산하는 generated 컬럼. 서버에서 필터·정렬·페이지 나누기용.
  apply_rate numeric generated always as (
    case when recruit_count > 0 and applicant_count is not null then applicant_count::numeric / recruit_count end
  ) stored,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 필터 조회 성능용 인덱스
create index if not exists campaigns_deadline_idx on public.campaigns (deadline_date);
create index if not exists campaigns_region_idx on public.campaigns (region_sido, region_gugun);
create index if not exists campaigns_category_idx on public.campaigns (category);
create index if not exists campaigns_platform_idx on public.campaigns (platform);
create index if not exists campaigns_last_seen_idx on public.campaigns (last_seen_at);
create index if not exists campaigns_active_apply_rate_idx on public.campaigns (apply_rate) where is_active;
create index if not exists campaigns_active_deadline_idx on public.campaigns (deadline_date) where is_active;
create index if not exists campaigns_type_idx on public.campaigns (campaign_type);
create index if not exists campaigns_guguns_idx on public.campaigns using gin (region_guguns);
create index if not exists campaigns_channels_idx on public.campaigns using gin (review_channels);

-- RLS: 프론트(anon key)는 읽기만, 쓰기는 service_role(크롤러)만
alter table public.campaigns enable row level security;

create policy "campaigns are publicly readable"
  on public.campaigns for select
  using (true);

-- updated_at 자동 갱신
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists campaigns_set_updated_at on public.campaigns;
create trigger campaigns_set_updated_at
  before update on public.campaigns
  for each row execute function public.set_updated_at();

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

-- 필터 선택지 집계 (src/lib/campaigns.ts fetchFilterOptions) — supabase/migrations/20261106_campaign_filter_options.sql
-- 필터 선택지(지역·시군구 건수·분류·유형·채널)를 DB에서 한 번에 집계한다.
-- 예전엔 앱이 모집 중 행을 전부 받아 직접 셌는데, PostgREST 기본 한도(1,000행) 때문에 일부만 보였다.
create or replace function public.campaign_filter_options()
returns json
language sql
stable
security invoker
set search_path = public
as $$
  with active as (
    select region_sido, region_guguns, category, campaign_type, review_channels, apply_rate
    from public.campaigns
    where is_active
  )
  select json_build_object(
    'sidos', coalesce((select json_agg(distinct region_sido) from active where region_sido is not null), '[]'::json),
    'guguns', coalesce((
      select json_object_agg(region_sido, items)
      from (
        select region_sido, json_agg(json_build_object('name', g, 'count', n) order by n desc, g) as items
        from (
          select region_sido, g, count(*) as n
          from active, unnest(region_guguns) as g
          where region_sido is not null
          group by region_sido, g
        ) c
        group by region_sido
      ) per_sido
    ), '{}'::json),
    'categories', coalesce((select json_agg(distinct category) from active where category is not null), '[]'::json),
    'types', coalesce((select json_agg(distinct campaign_type) from active where campaign_type is not null), '[]'::json),
    'channels', coalesce((select json_agg(distinct c) from active, unnest(review_channels) as c), '[]'::json),
    -- 경쟁률 슬라이더의 오른쪽 끝 = 지금 모집 중인 체험단의 최대 경쟁률
    'maxApplyRate', coalesce((select ceil(max(apply_rate)) from active), 10)
  );
$$;

grant execute on function public.campaign_filter_options() to anon, authenticated;

-- 정렬 보조 순서(src/lib/campaigns.ts SORT_CHAINS)에 맞춘 복합 인덱스
create index if not exists campaigns_active_deadline_chain_idx
  on public.campaigns (deadline_date asc nulls last, apply_rate asc nulls last, recruit_count desc nulls last, created_at desc, id)
  where is_active;
create index if not exists campaigns_active_rate_chain_idx
  on public.campaigns (apply_rate asc nulls last, deadline_date asc nulls last, recruit_count desc nulls last, created_at desc, id)
  where is_active;

-- 그 회차에 목록에서 사라져 모집 종료 처리한 캠페인 수 (scraper/loader.py close_unseen)
alter table public.scrape_runs add column if not exists closed_count integer not null default 0;
