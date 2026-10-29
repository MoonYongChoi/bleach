-- 데이터 정제 (scraper/normalize.py) 도입에 따른 컬럼 추가 + 기존 행 정리.
-- Supabase SQL Editor에서 한 번 실행하세요. 여러 번 실행해도 안전합니다.

alter table public.campaigns add column if not exists category_raw text;
alter table public.campaigns add column if not exists campaign_type text;

create index if not exists campaigns_type_idx on public.campaigns (campaign_type);

-- 기존 category에는 플랫폼 원본값이 들어 있으므로 category_raw로 보존한다.
-- (표준 분류는 다음 스크래핑에서 normalize.py가 다시 채운다.)
update public.campaigns
set category_raw = category
where category_raw is null
  and category is not null
  and category not in ('맛집','카페·디저트','뷰티','여행·숙박','식품·배송','디지털','생활','문화·여가');

-- 레뷰 "제품"/"지역", 리뷰노트 sort, 파블로 "배송" 등으로 유형을 미리 채운다.
update public.campaigns
set campaign_type = case
    when category_raw = '제품' or region_gugun = '배송' or category_raw = '배송' then '배송'
    when region_gugun = '기자단' then '기자단'
    when category_raw = '지역' or region_sido is not null then '방문'
    else '기타'
  end
where campaign_type is null;

-- 지역 칸에 들어가 있던 유형 라벨 제거
update public.campaigns
set region_gugun = null
where region_gugun in ('배송', '기자단', '실시간', '누구나', '전국', '재택', '구매평');

-- 리뷰노트 제목에 붙어 있던 " - 제공내역" 제거
update public.campaigns
set title = left(title, length(title) - length(description) - 3)
where platform = '리뷰노트'
  and description is not null
  and title like '% - ' || description
  and length(title) > length(description) + 3;

-- 마감 지난 건 내리기 (KST 기준)
update public.campaigns
set is_active = false
where is_active
  and deadline_date < (now() at time zone 'Asia/Seoul')::date;
