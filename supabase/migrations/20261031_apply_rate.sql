-- 경쟁률(모집 1명당 신청자 수). 서버에서 필터·정렬·페이지 나누기를 하려고 DB가 계산해 둔다.
-- 신청/모집 인원 중 하나라도 없으면 NULL. 로더는 이 컬럼에 쓰지 않는다 (generated).
alter table public.campaigns
  add column if not exists apply_rate numeric
  generated always as (
    case when recruit_count > 0 and applicant_count is not null
      then applicant_count::numeric / recruit_count end
  ) stored;

create index if not exists campaigns_active_apply_rate_idx on public.campaigns (apply_rate) where is_active;
create index if not exists campaigns_active_deadline_idx on public.campaigns (deadline_date) where is_active;
