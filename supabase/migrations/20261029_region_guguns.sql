-- 하위 지역(시/군/구) 필터용 배열. region_gugun "서초구/강남구" -> {서초구,강남구}
-- 문자열 LIKE 검색은 "서구"가 "강서구"에 걸리므로 배열의 정확한 원소 비교(@>)로 거른다.
-- 여러 번 실행해도 안전합니다.

alter table public.campaigns add column if not exists region_guguns text[] not null default '{}';

update public.campaigns
set region_guguns = string_to_array(region_gugun, '/')
where region_gugun is not null and region_sido is not null and region_guguns = '{}';

create index if not exists campaigns_guguns_idx on public.campaigns using gin (region_guguns);
