-- 그 회차에 목록에서 사라져 모집 종료 처리한 캠페인 수 (scraper/loader.py close_unseen)
alter table public.scrape_runs add column if not exists closed_count integer not null default 0;
