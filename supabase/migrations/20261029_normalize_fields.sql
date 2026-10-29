-- 데이터 정제 (scraper/normalize.py) 도입에 따른 컬럼 추가.
-- 여러 번 실행해도 안전합니다.
--
-- 기존 행의 값 정제(분류/지역/제목/유형/비활성화)는 SQL로 흉내 내지 않고
-- scraper/backfill.py 로 normalize.py와 같은 규칙을 적용합니다:
--   cd scraper && python backfill.py          # 미리보기
--   cd scraper && python backfill.py --apply  # 적용

alter table public.campaigns add column if not exists category_raw text;
alter table public.campaigns add column if not exists campaign_type text;

create index if not exists campaigns_type_idx on public.campaigns (campaign_type);
