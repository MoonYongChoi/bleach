-- 리뷰 채널(블로그/인스타/릴스/유튜브/쇼츠/틱톡/클립) — 한 캠페인이 여러 채널을 요구할 수 있어 배열.
-- 값은 scraper/normalize.py REVIEW_CHANNELS 의 코드. 비어 있으면 "플랫폼이 채널 정보를 안 줌".
-- 여러 번 실행해도 안전합니다.

alter table public.campaigns add column if not exists review_channels text[] not null default '{}';

create index if not exists campaigns_channels_idx on public.campaigns using gin (review_channels);
