-- 방문자 브라우저가 직접 못 받는 썸네일(모두블로그: 쿠키 없는 요청에 봇 확인 HTML)을 수집기가 받아 둔다.
-- 사이트는 /api/thumb?u=<원래 주소> 로 꺼내 보여 준다. 수집기(scraper/loader.py save_thumbs)가 처음 쓸 때 이 테이블을 만든다.
create table if not exists public.thumb_cache (
  url text primary key,
  content_type text not null,
  bytes bytea not null,
  fetched_at timestamptz not null default now()
);
alter table public.thumb_cache enable row level security;
do $$ begin
  if not exists (select 1 from pg_policies where tablename = 'thumb_cache' and policyname = 'thumb_cache is readable') then
    create policy "thumb_cache is readable" on public.thumb_cache for select using (true);
  end if;
end $$;
grant select on public.thumb_cache to anon, authenticated;
