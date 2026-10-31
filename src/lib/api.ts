import {
  countCampaigns,
  encodeFilters,
  fetchCampaignPage,
  type Campaign,
  type CampaignFilters,
  type FilterOptions,
} from "@/lib/campaigns";

// 브라우저에서 쓰는 조회 함수. 서버 경로(/api/...)를 거쳐 CDN·서버 캐시를 타고, Supabase는 캐시가 빗나갔을 때만 호출된다.
// 관심 목록 보기(ids)는 기기마다 값이 달라 캐시할 수 없어서 예전처럼 Supabase를 직접 부른다.

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export function loadFilterOptions(): Promise<FilterOptions> {
  return getJson<FilterOptions>("/api/filter-options");
}

export async function loadCampaignPage(filters: CampaignFilters, page: number): Promise<Campaign[]> {
  if (filters.ids) return fetchCampaignPage(filters, page);
  const q = encodeURIComponent(encodeFilters(filters));
  return (await getJson<{ rows: Campaign[] }>(`/api/campaigns?q=${q}&page=${page}`)).rows;
}

export async function loadCampaignCount(filters: CampaignFilters): Promise<number> {
  if (filters.ids) return countCampaigns(filters);
  const q = encodeURIComponent(encodeFilters(filters));
  return (await getJson<{ total: number }>(`/api/campaigns/count?q=${q}`)).total;
}
