import { CATEGORIES } from "@/lib/categories";
import { supabase } from "@/lib/supabase";

export interface Campaign {
  id: string;
  platform: string;
  title: string;
  region_sido: string | null;
  region_gugun: string | null;
  deadline_date: string | null;
  announce_date: string | null;
  source_url: string;
  category: string | null;
  /** 방문 / 배송 / 기자단 / 기타 — scraper/normalize.py가 채운다 */
  campaign_type: string | null;
  description: string | null;
  image_url: string | null;
  vendor: string | null;
  recruit_count: number | null;
  applicant_count: number | null;
  created_at: string;
}

export type SortOption = "deadline" | "latest";

export interface ApplyRateRange {
  min: number;
  max: number;
}

export interface CampaignFilters {
  search?: string;
  sidos?: string[];
  categories?: string[];
  platforms?: string[];
  applyRate?: ApplyRateRange;
  sort?: SortOption;
}

/** 체험단 플랫폼 — 스크래퍼가 고정으로 다루는 3곳이라 DB 조회 없이 상수로 둔다. */
export const PLATFORMS = ["레뷰", "파블로", "리뷰노트"] as const;

const SELECT_COLUMNS =
  "id, platform, title, region_sido, region_gugun, deadline_date, announce_date, source_url, category, campaign_type, description, image_url, vendor, recruit_count, applicant_count, created_at";

export async function fetchCampaigns(filters: CampaignFilters = {}): Promise<Campaign[]> {
  // 지역/카테고리/업체/검색은 모두 AND로 묶여 DB에서 같이 걸러진다 (PostgREST의
  // 연속된 .in()/.ilike() 호출은 SQL WHERE ... AND ... 로 합쳐진다).
  let query = supabase.from("campaigns").select(SELECT_COLUMNS).eq("is_active", true);

  if (filters.search) {
    query = query.ilike("title", `%${filters.search}%`);
  }
  if (filters.sidos && filters.sidos.length > 0) {
    query = query.in("region_sido", filters.sidos);
  }
  if (filters.categories && filters.categories.length > 0) {
    query = query.in("category", filters.categories);
  }
  if (filters.platforms && filters.platforms.length > 0) {
    query = query.in("platform", filters.platforms);
  }

  if (filters.sort === "deadline") {
    query = query.order("deadline_date", { ascending: true, nullsFirst: false });
  } else {
    query = query.order("created_at", { ascending: false });
  }

  // 테이블이 아직 작아서(수백 건) 넉넉히 받아온 뒤 지원률은 클라이언트에서 추가로
  // 거른다. 같은 스크래핑 배치로 들어온 행은 created_at이 트랜잭션 단위로 동일해서,
  // limit을 너무 타이트하게 두면 동점 처리 순서상 특정 행들이 통째로 잘릴 수 있다.
  const { data, error } = await query.limit(1000);
  if (error) throw error;

  // 지원률(applicant_count / recruit_count)은 계산된 값이라 PostgREST where절로
  // 못 걸러서, 위 필터들과 AND로 합쳐지도록 클라이언트에서 한 번 더 좁힌다.
  const rows = data ?? [];
  if (!filters.applyRate) return rows;
  return rows.filter((row) => {
    const rate = applyRate(row);
    if (rate === null) return false;
    return rate >= filters.applyRate!.min && rate <= filters.applyRate!.max;
  });
}

export async function fetchFilterOptions(): Promise<{
  sidos: string[];
  categories: string[];
}> {
  const { data, error } = await supabase
    .from("campaigns")
    .select("region_sido, category")
    .eq("is_active", true);
  if (error) throw error;

  const sidos = new Set<string>();
  const categories = new Set<string>();
  for (const row of data ?? []) {
    if (row.region_sido) sidos.add(row.region_sido);
    if (row.category) categories.add(row.category);
  }
  // 카테고리는 스크래퍼가 표준 8종 라벨로 정규화해 두므로 categories.ts의 정의 순서대로 노출한다.
  const order = CATEGORIES.map((c) => c.label);
  const rank = (label: string) => (order.indexOf(label) === -1 ? order.length : order.indexOf(label));
  return {
    sidos: [...sidos].sort(),
    categories: [...categories].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b)),
  };
}

/** 지원률 = 현재 신청(대기)인원 / 전체 모집인원. 둘 중 하나라도 없으면 null. */
export function applyRate(campaign: Pick<Campaign, "recruit_count" | "applicant_count">): number | null {
  if (!campaign.recruit_count || campaign.applicant_count === null) return null;
  return campaign.applicant_count / campaign.recruit_count;
}

export function dDay(deadlineDate: string | null): number | null {
  if (!deadlineDate) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const deadline = new Date(deadlineDate);
  deadline.setHours(0, 0, 0, 0);
  return Math.round((deadline.getTime() - today.getTime()) / 86400000);
}
