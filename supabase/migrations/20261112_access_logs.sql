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
