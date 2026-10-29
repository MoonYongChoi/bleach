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

  -- 4. 일정/마감일
  deadline_date date,
  announce_date date,

  -- 5. 원문 URL (Outlink) — 중복 수집 방지를 위한 unique 키
  source_url text not null unique,

  -- 표준 분류 8종 (scraper/normalize.py STANDARD_CATEGORIES = src/lib/categories.ts 라벨)
  category text,
  -- 플랫폼 원본 분류 텍스트 (디버깅/재분류용)
  category_raw text,
  -- 캠페인 유형: 방문 / 배송 / 기자단 / 기타 (배송형은 지역 없음)
  campaign_type text,

  -- 6. 제공내역(체험단 상세 혜택 설명) / 목록 썸네일
  description text,
  image_url text,

  -- 7. 업체명 / 지원 현황 (지원률 = applicant_count / recruit_count)
  vendor text,
  recruit_count integer,
  applicant_count integer,

  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 필터 조회 성능용 인덱스
create index if not exists campaigns_deadline_idx on public.campaigns (deadline_date);
create index if not exists campaigns_region_idx on public.campaigns (region_sido, region_gugun);
create index if not exists campaigns_category_idx on public.campaigns (category);
create index if not exists campaigns_platform_idx on public.campaigns (platform);
create index if not exists campaigns_type_idx on public.campaigns (campaign_type);

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
