-- 수집 목록에서 마지막으로 확인된 시각. updated_at은 수동 수정·백필에도 바뀌어서
-- "한동안 목록에서 안 보인 캠페인"을 가리는 용도로 믿을 수 없다 (2026-10-31).
-- scraper/loader.py가 upsert할 때만 갱신한다.
-- 컬럼이 처음 생길 때만 기존 값을 채우므로 여러 번 실행해도 안전합니다.

do $$
begin
  if not exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'campaigns' and column_name = 'last_seen_at'
  ) then
    alter table public.campaigns add column last_seen_at timestamptz not null default now();
    update public.campaigns set last_seen_at = updated_at;  -- SET은 수정 전 값을 읽는다
  end if;
end $$;

create index if not exists campaigns_last_seen_idx on public.campaigns (last_seen_at);
