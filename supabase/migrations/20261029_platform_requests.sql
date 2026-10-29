-- 사용자가 "이 체험단 사이트도 모아주세요"라고 요청하는 테이블.
-- 공개 키(anon)로는 넣기만 가능하고 읽을 수 없다 (요청자 연락처 보호). 확인은 대시보드/서비스 키로.
-- 여러 번 실행해도 안전합니다.

create table if not exists public.platform_requests (
  id uuid primary key default gen_random_uuid(),
  site_name text not null check (char_length(site_name) between 1 and 100),
  site_url text check (site_url is null or char_length(site_url) <= 500),
  note text check (note is null or char_length(note) <= 1000),
  contact_email text check (contact_email is null or char_length(contact_email) <= 200),
  status text not null default 'new',  -- new / reviewing / added / rejected
  created_at timestamptz not null default now()
);

alter table public.platform_requests enable row level security;

drop policy if exists "anyone can submit a platform request" on public.platform_requests;
create policy "anyone can submit a platform request"
  on public.platform_requests for insert
  to anon, authenticated
  with check (status = 'new');
