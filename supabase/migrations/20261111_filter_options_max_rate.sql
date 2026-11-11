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
