-- 마감일이 지난 캠페인 내리기를 수집과 따로, DB가 직접 한다 (GitHub 예약 수집은 몇 시간씩 늦거나 빠진다).
-- 매시 1분 (자정 00:01 KST 포함). KST 기준 오늘보다 마감일이 이른 모집 중 캠페인을 내린다.
select cron.unschedule(jobid) from cron.job where jobname = 'expire_campaigns';
select cron.schedule('expire_campaigns', '1 * * * *', $$
  update public.campaigns set is_active = false
  where is_active and deadline_date < (now() at time zone 'Asia/Seoul')::date
$$);
