-- 정렬 보조 순서(src/lib/campaigns.ts SORT_CHAINS)에 맞춘 복합 인덱스
create index if not exists campaigns_active_deadline_chain_idx
  on public.campaigns (deadline_date asc nulls last, apply_rate asc nulls last, recruit_count desc nulls last, created_at desc, id)
  where is_active;
create index if not exists campaigns_active_rate_chain_idx
  on public.campaigns (apply_rate asc nulls last, deadline_date asc nulls last, recruit_count desc nulls last, created_at desc, id)
  where is_active;
