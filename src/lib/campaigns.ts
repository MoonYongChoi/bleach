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
  /** 방문 / 배송 / 구매 / 기자단 / 기타 — scraper/normalize.py가 채운다 */
  campaign_type: string | null;
  /** blog / instagram / reels / youtube / shorts / tiktok / clip */
  review_channels: string[];
  description: string | null;
  image_url: string | null;
  vendor: string | null;
  recruit_count: number | null;
  applicant_count: number | null;
  created_at: string;
}

/**
 * deadline: 마감일 가까운 순 / latest: 새로 올라온 순
 * competition: 지원률(신청÷모집) 낮은 순 — 붙을 확률이 높은 것부터 / recruit: 모집인원 많은 순
 */
export type SortOption = "deadline" | "latest" | "competition" | "recruit";

export const SORT_OPTIONS: { value: SortOption; label: string; hint: string }[] = [
  { value: "deadline", label: "마감임박순", hint: "마감일이 가까운 체험단부터" },
  { value: "competition", label: "경쟁 낮은순", hint: "모집인원 대비 신청자가 적은 순" },
  { value: "recruit", label: "모집인원 많은순", hint: "한 번에 많이 뽑는 체험단부터" },
  { value: "latest", label: "최신 등록순", hint: "BLEACH에 새로 올라온 순" },
];

export interface ApplyRateRange {
  min: number;
  max: number;
}

export interface CampaignFilters {
  search?: string;
  /** 시/도 전체 선택 */
  sidos?: string[];
  /** 하위 지역 선택: "경기 하남시" 형태 (시/도 + 공백 + 시/군/구). 같은 시/도가 sidos에 있으면 무시 */
  guguns?: string[];
  categories?: string[];
  platforms?: string[];
  types?: string[];
  channels?: string[];
  applyRate?: ApplyRateRange;
  /** false면 마감일 없는(상시모집) 체험단을 뺀다. 마감임박순에서만 쓰인다 */
  includeOpenEnded?: boolean;
  /** 지정하면 이 id들만 (관심 목록 보기) */
  ids?: string[];
  sort?: SortOption;
}

/** 체험단 플랫폼 — scraper/connectors/__init__.py REGISTRY의 label과 같은 순서로 맞춘다. */
export const PLATFORMS = ["레뷰", "파블로", "리뷰노트", "디너의여왕", "모두블로그"] as const;

/** campaign_type 값 → 화면 표시 (사용자가 고르는 기준인 "무엇을 하게 되는가"로 이름 붙임) */
export const CAMPAIGN_TYPE_LABELS: Record<string, { label: string; hint: string }> = {
  방문: { label: "방문 체험", hint: "매장에 가서 체험" },
  배송: { label: "제품 제공", hint: "집으로 받아서 사용" },
  구매: { label: "구매 후 환급", hint: "직접 사고 돌려받기" },
  기자단: { label: "기자단", hint: "체험 없이 원고만" },
};

/** review_channels 코드 → 화면 표시. scraper/normalize.py REVIEW_CHANNELS와 같은 순서. */
export const REVIEW_CHANNEL_LABELS: Record<string, string> = {
  blog: "블로그",
  instagram: "인스타그램",
  reels: "릴스",
  youtube: "유튜브",
  shorts: "쇼츠",
  tiktok: "틱톡",
  clip: "클립",
};

const SELECT_COLUMNS =
  "id, platform, title, region_sido, region_gugun, deadline_date, announce_date, source_url, category, campaign_type, review_channels, image_url, vendor, recruit_count, applicant_count, created_at";

/** 목록에서 한 번에 불러오는 개수 (스크롤이 끝에 가까워질 때마다 이만큼씩 더 받는다) */
export const PAGE_SIZE = 30;

/**
 * 검색·필터를 DB 쿼리에 적용한다 (정렬·페이지 제외). 목록과 "총 N개" 조회가 같은 조건을 쓰도록 한 곳에 둔다.
 * 지역/카테고리/업체/유형/채널/검색은 모두 AND로 묶여 DB에서 같이 걸러진다 (PostgREST의 연속된 필터 호출은
 * SQL WHERE ... AND ... 로 합쳐진다). 같은 항목 안의 복수 선택은 OR.
 */
function filteredQuery(filters: CampaignFilters, columns: string, options?: { count: "exact"; head: boolean }) {
  let query = supabase.from("campaigns").select(columns, options).eq("is_active", true);

  if (filters.search) {
    query = query.ilike("title", `%${filters.search}%`);
  }
  const regionClause = buildRegionClause(filters.sidos ?? [], filters.guguns ?? []);
  if (regionClause) {
    query = query.or(regionClause);
  }
  if (filters.categories && filters.categories.length > 0) {
    query = query.in("category", filters.categories);
  }
  if (filters.platforms && filters.platforms.length > 0) {
    query = query.in("platform", filters.platforms);
  }
  if (filters.types && filters.types.length > 0) {
    query = query.in("campaign_type", filters.types);
  }
  if (filters.channels && filters.channels.length > 0) {
    // 고른 채널 중 하나라도 요구하는 캠페인 (배열 교집합)
    query = query.overlaps("review_channels", filters.channels);
  }
  if (filters.ids) {
    query = query.in("id", filters.ids);
  }
  if (filters.sort === "deadline" && filters.includeOpenEnded === false) {
    query = query.not("deadline_date", "is", null);
  }

  // 경쟁률은 DB가 계산해 둔 apply_rate 컬럼으로 거른다 (값이 없는 캠페인은 자연히 빠진다)
  if (filters.applyRate) {
    query = query.gte("apply_rate", filters.applyRate.min);
    if (Number.isFinite(filters.applyRate.max)) query = query.lte("apply_rate", filters.applyRate.max);
  }
  return query;
}

/** 조건에 맞는 캠페인 수 ("총 N개"와 필터 시트의 "N개 결과 보기"). */
export async function countCampaigns(filters: CampaignFilters = {}): Promise<number> {
  if (filters.ids && filters.ids.length === 0) return 0;
  const { count, error } = await filteredQuery(filters, "id", { count: "exact", head: true });
  if (error) throw error;
  return count ?? 0;
}

/** 정렬된 목록의 page번째 묶음(0부터). PAGE_SIZE보다 적게 오면 마지막 페이지다. */
export async function fetchCampaignPage(filters: CampaignFilters = {}, page = 0): Promise<Campaign[]> {
  if (filters.ids && filters.ids.length === 0) return [];

  let query = filteredQuery(filters, SELECT_COLUMNS);
  switch (filters.sort) {
    case "deadline":
      // 상시모집(마감일 없음)은 맨 뒤로
      query = query.order("deadline_date", { ascending: true, nullsFirst: false });
      break;
    case "recruit":
      query = query.order("recruit_count", { ascending: false, nullsFirst: false });
      break;
    case "competition":
      // 경쟁률을 모르는 체험단은 맨 뒤로
      query = query.order("apply_rate", { ascending: true, nullsFirst: false });
      break;
  }
  // 같은 값 안에서는 최신 등록순, 마지막은 id — 같은 배치로 들어온 행은 created_at이 같아서 id로 순서를 고정해야
  // 페이지 경계에서 행이 겹치거나 빠지지 않는다
  query = query.order("created_at", { ascending: false }).order("id");

  const from = page * PAGE_SIZE;
  const { data, error } = await query.range(from, from + PAGE_SIZE - 1);
  if (error) throw error;
  return (data ?? []) as unknown as Campaign[];
}

/**
 * 지역 선택 → PostgREST or() 조건. 예) 서울 전체 + 경기 하남시·수원시:
 *   region_sido.in.(서울),and(region_sido.eq.경기,region_guguns.ov.{하남시,수원시})
 */
function buildRegionClause(sidos: string[], guguns: string[]): string | null {
  const bySido = new Map<string, string[]>();
  for (const key of guguns) {
    const [sido, gugun] = splitGugunKey(key);
    if (!sido || !gugun || sidos.includes(sido)) continue;
    bySido.set(sido, [...(bySido.get(sido) ?? []), gugun]);
  }
  const parts: string[] = [];
  if (sidos.length > 0) parts.push(`region_sido.in.(${sidos.join(",")})`);
  for (const [sido, list] of bySido) {
    parts.push(`and(region_sido.eq.${sido},region_guguns.ov.{${list.join(",")}})`);
  }
  return parts.length > 0 ? parts.join(",") : null;
}

export function gugunKey(sido: string, gugun: string) {
  return `${sido} ${gugun}`;
}

export function splitGugunKey(key: string): [string, string] {
  const i = key.indexOf(" ");
  return [key.slice(0, i), key.slice(i + 1)];
}

export interface FilterOptions {
  sidos: string[];
  /** 시/도별 하위 지역 (실제 데이터에 있는 것만, 체험단 많은 순) */
  guguns: Record<string, { name: string; count: number }[]>;
  categories: string[];
  types: string[];
  channels: string[];
}

export async function fetchFilterOptions(): Promise<FilterOptions> {
  const { data, error } = await supabase
    .from("campaigns")
    .select("region_sido, region_guguns, category, campaign_type, review_channels")
    .eq("is_active", true);
  if (error) throw error;

  const sidos = new Set<string>();
  const categories = new Set<string>();
  const types = new Set<string>();
  const channels = new Set<string>();
  const gugunCounts = new Map<string, Map<string, number>>();
  for (const row of data ?? []) {
    if (row.region_sido) {
      sidos.add(row.region_sido);
      const counts = gugunCounts.get(row.region_sido) ?? new Map<string, number>();
      for (const g of row.region_guguns ?? []) counts.set(g, (counts.get(g) ?? 0) + 1);
      gugunCounts.set(row.region_sido, counts);
    }
    if (row.category) categories.add(row.category);
    if (row.campaign_type && row.campaign_type in CAMPAIGN_TYPE_LABELS) types.add(row.campaign_type);
    for (const c of row.review_channels ?? []) if (c in REVIEW_CHANNEL_LABELS) channels.add(c);
  }

  // 실제 데이터에 있는 값만 보여주되, 순서는 정의된 표준 순서를 따른다.
  const byOrder = (order: string[]) => (a: string, b: string) => {
    const rank = (v: string) => (order.indexOf(v) === -1 ? order.length : order.indexOf(v));
    return rank(a) - rank(b) || a.localeCompare(b);
  };
  return {
    sidos: [...sidos].sort(byOrder(SIDO_ORDER)),
    guguns: Object.fromEntries(
      [...gugunCounts].map(([sido, counts]) => [
        sido,
        [...counts]
          .map(([name, count]) => ({ name, count }))
          .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name)),
      ])
    ),
    categories: [...categories].sort(byOrder(CATEGORIES.map((c) => c.label))),
    types: [...types].sort(byOrder(Object.keys(CAMPAIGN_TYPE_LABELS))),
    channels: [...channels].sort(byOrder(Object.keys(REVIEW_CHANNEL_LABELS))),
  };
}

// 가나다순이 아니라 사람들이 익숙한 행정구역 순서 (수도권 → 광역시 → 도 → 해외)
const SIDO_ORDER = [
  "서울", "경기", "인천", "부산", "대구", "광주", "대전", "울산", "세종",
  "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
  "해외", // 해외 방문 체험 — 하위 지역 칸에 나라 이름 (일본, 베트남 …)
];

/** 지원률 = 현재 신청(대기)인원 / 전체 모집인원. 둘 중 하나라도 없으면 null. */
export function applyRate(campaign: Pick<Campaign, "recruit_count" | "applicant_count">): number | null {
  if (!campaign.recruit_count || campaign.applicant_count === null) return null;
  return campaign.applicant_count / campaign.recruit_count;
}

/** 경쟁률 표기: 1 미만은 자리가 남는다는 뜻이라 "여유", 그 외는 "3.2:1". */
export function formatCompetition(rate: number | null): string | null {
  if (rate === null) return null;
  if (rate < 1) return "여유";
  return `${rate >= 10 ? Math.round(rate) : Math.round(rate * 10) / 10}:1`;
}

/** 오늘 날짜 "YYYY-MM-DD" — 보는 사람 기기의 시간대와 상관없이 한국 시간 기준 */
export function todayKst(): string {
  // en-CA 로케일은 YYYY-MM-DD 형식으로 날짜를 준다
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul" }).format(new Date());
}

/** 마감까지 남은 일수 (한국 시간 기준). deadline_date는 이미 KST 날짜로 저장돼 있다. */
export function dDay(deadlineDate: string | null): number | null {
  if (!deadlineDate) return null;
  // 두 날짜를 모두 UTC 자정으로 놓고 빼면 기기 시간대·서머타임 영향 없이 날짜 차이만 남는다
  const toUtc = (ymd: string) => {
    const [y, m, d] = ymd.slice(0, 10).split("-").map(Number);
    return Date.UTC(y, m - 1, d);
  };
  return Math.round((toUtc(deadlineDate) - toUtc(todayKst())) / 86400000);
}
