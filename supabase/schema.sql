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

-- 사용자 이용 기록 (페이지 방문·검색·필터·체험단 클릭). 브라우저 → /api/log → log_event() 로만 쌓인다.
-- IP·쿠키·로그인 정보는 저장하지 않는다. session은 브라우저 탭마다 새로 만드는 임의 값.
create table if not exists public.access_logs (
  id bigint generated always as identity primary key,
  ts timestamptz not null default now(),
  event text not null check (event in ('page_view', 'search', 'filter', 'click')),
  session text not null,
  path text,
  referrer text,      -- 유입 도메인만 (예: m.search.naver.com)
  device text,        -- mobile / desktop
  country text,       -- Vercel이 붙여 주는 국가 코드 (예: KR)
  data jsonb not null default '{}'::jsonb
);
create index if not exists access_logs_ts_idx on public.access_logs (ts desc);
create index if not exists access_logs_event_ts_idx on public.access_logs (event, ts desc);
create index if not exists access_logs_session_ts_idx on public.access_logs (session, ts desc);

-- 정책을 두지 않는다 = anon/authenticated는 직접 읽거나 쓸 수 없다. 쓰기는 log_event(), 읽기는 집계 함수로만.
alter table public.access_logs enable row level security;

create or replace function public.log_event(
  p_event text, p_session text, p_path text, p_referrer text, p_device text, p_country text, p_data jsonb
) returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if p_event not in ('page_view', 'search', 'filter', 'click')
     or p_session is null or length(p_session) not between 8 and 64 then
    return;
  end if;
  -- 같은 탭에서 같은 이벤트가 1초 안에 또 오면 버린다 (중복 전송·연타)
  if exists (
    select 1 from public.access_logs
    where session = p_session and event = p_event and ts > now() - interval '1 second'
      and coalesce(path, '') = coalesce(left(p_path, 200), '')
  ) then
    return;
  end if;
  insert into public.access_logs (event, session, path, referrer, device, country, data)
  values (
    p_event, p_session, left(p_path, 200), left(p_referrer, 100), left(p_device, 10), left(p_country, 4),
    case when p_data is null or length(p_data::text) > 1000 then '{}'::jsonb else p_data end
  );
end;
$$;
revoke all on function public.log_event(text, text, text, text, text, text, jsonb) from public;
grant execute on function public.log_event(text, text, text, text, text, text, jsonb) to anon, authenticated;

-- ---- /admin/logs 용 집계 (원본 행은 내보내지 않는다) ----

-- 일별: 방문자(탭 수), 페이지뷰, 검색, 필터, 클릭 (KST 날짜)
create or replace function public.admin_log_daily(p_days int default 30)
returns table (day date, visitors bigint, page_views bigint, searches bigint, filters bigint, clicks bigint)
language sql stable security definer set search_path = public
as $$
  select (ts at time zone 'Asia/Seoul')::date as day,
         count(distinct session),
         count(*) filter (where event = 'page_view'),
         count(*) filter (where event = 'search'),
         count(*) filter (where event = 'filter'),
         count(*) filter (where event = 'click')
  from public.access_logs
  where ts > now() - make_interval(days => least(greatest(p_days, 1), 90))
  group by 1 order by 1 desc;
$$;

-- 순위: referrer / search / filter / click_platform / click_campaign / device / country
create or replace function public.admin_log_top(p_kind text, p_days int default 7, p_limit int default 20)
returns table (label text, n bigint)
language sql stable security definer set search_path = public
as $$
  with recent as (
    select * from public.access_logs
    where ts > now() - make_interval(days => least(greatest(p_days, 1), 90))
  ), labeled as (
    select case p_kind
      when 'referrer' then case when event = 'page_view' then coalesce(nullif(referrer, ''), '(직접 방문)') end
      when 'search' then case when event = 'search' then lower(data->>'q') end
      when 'filter' then case when event = 'filter' then data->>'summary' end
      when 'click_platform' then case when event = 'click' then data->>'platform' end
      when 'click_campaign' then case when event = 'click' then concat(data->>'platform', ' · ', data->>'title') end
      when 'device' then case when event = 'page_view' then device end
      when 'country' then case when event = 'page_view' then country end
    end as label
    from recent
  )
  select label, count(*) from labeled where label is not null and label <> ''
  group by label order by count(*) desc, label limit least(greatest(p_limit, 1), 100);
$$;

-- 최근 이벤트 (세션은 앞 6자리만)
create or replace function public.admin_log_recent(p_limit int default 50)
returns table (ts timestamptz, event text, session text, path text, referrer text, device text, data jsonb)
language sql stable security definer set search_path = public
as $$
  select ts, event, left(session, 6), path, referrer, device, data
  from public.access_logs order by ts desc limit least(greatest(p_limit, 1), 200);
$$;

grant execute on function public.admin_log_daily(int), public.admin_log_top(text, int, int), public.admin_log_recent(int)
  to anon, authenticated;

-- 90일 지난 기록은 매일 04:10 KST(19:10 UTC)에 지운다
create extension if not exists pg_cron;
select cron.unschedule(jobid) from cron.job where jobname = 'access_logs_retention';
select cron.schedule('access_logs_retention', '10 19 * * *',
  $$delete from public.access_logs where ts < now() - interval '90 days'$$);
