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

/** 정렬 기준. 각 기준은 방향(SortDir)을 따로 가진다 — 예) 마감: 임박(asc) / 여유(desc) */
export type SortOption = "deadline" | "latest" | "competition" | "recruit";
export type SortDir = "asc" | "desc";
export type SortDirs = Record<SortOption, SortDir>;

/** 기본 방향: 모두 "신청자에게 유리한 쪽 먼저" */
export const DEFAULT_SORT_DIRS: SortDirs = {
  deadline: "asc", // 마감 임박
  competition: "asc", // 경쟁 낮은
  recruit: "desc", // 모집인원 많은
  latest: "desc", // 최신 등록
};

/** 정렬 시트에 나오는 순서와 이름. 첫 번째 방향이 기본값이다. */
export const SORT_CRITERIA: { value: SortOption; title: string; dirs: { dir: SortDir; label: string }[] }[] = [
  { value: "deadline", title: "마감", dirs: [{ dir: "asc", label: "임박" }, { dir: "desc", label: "여유" }] },
  { value: "competition", title: "경쟁", dirs: [{ dir: "asc", label: "낮은" }, { dir: "desc", label: "높은" }] },
  { value: "recruit", title: "모집인원", dirs: [{ dir: "desc", label: "많은" }, { dir: "asc", label: "적은" }] },
  { value: "latest", title: "등록일", dirs: [{ dir: "desc", label: "최신" }, { dir: "asc", label: "오래된" }] },
];

export function dirOf(dirs: Partial<SortDirs> | undefined, key: SortOption): SortDir {
  return dirs?.[key] ?? DEFAULT_SORT_DIRS[key];
}

/** 정렬 버튼에 쓰는 이름 (예: "마감 임박순", "경쟁 높은순") */
export function sortLabel(sort: SortOption, dirs?: Partial<SortDirs>): string {
  const c = SORT_CRITERIA.find((x) => x.value === sort)!;
  const d = c.dirs.find((x) => x.dir === dirOf(dirs, sort))!;
  return `${c.title} ${d.label}순`;
}

/**
 * 정렬 규칙: 고른 기준이 1순위, 같은 값끼리는 아래 순서로 나머지 기준을 쓴다 (각 기준은 고른 방향대로).
 * 경쟁률 필터를 걸었으면 경쟁률이 2순위로 온다. 지역·분류 같은 나머지 필터는 순서를 바꾸지 않는다.
 * 값이 없는 체험단(상시모집, 신청 현황 비공개 등)은 방향과 상관없이 그 기준에서 맨 뒤.
 */
const SORT_CHAINS: Record<SortOption, SortOption[]> = {
  deadline: ["deadline", "competition", "recruit", "latest"],
  competition: ["competition", "deadline", "recruit", "latest"],
  recruit: ["recruit", "competition", "deadline", "latest"],
  latest: ["latest", "deadline", "competition", "recruit"],
};

export function sortChain(sort: SortOption, hasRateFilter: boolean): SortOption[] {
  const [primary, ...rest] = SORT_CHAINS[sort];
  if (!hasRateFilter || primary === "competition") return [primary, ...rest];
  return [primary, "competition", ...rest.filter((k) => k !== "competition")];
}

// 정렬 시트 안내 문장: "{1순위가 같으면} {2순위} 체험단부터 보여줘요"
const SORT_KEY_SAME: Record<SortOption, string> = {
  deadline: "마감일이 같으면",
  competition: "경쟁률이 같으면",
  recruit: "모집인원이 같으면",
  latest: "같은 날 올라왔으면",
};
const SORT_KEY_FIRST: Record<SortOption, Record<SortDir, string>> = {
  deadline: { asc: "마감이 가까운", desc: "마감이 넉넉한" },
  competition: { asc: "경쟁이 낮은", desc: "경쟁이 높은" },
  recruit: { desc: "많이 뽑는", asc: "적게 뽑는" },
  latest: { desc: "최근 올라온", asc: "먼저 올라온" },
};

/** 정렬 시트에 보여 줄 보조 순서 안내 (예: "마감일이 같으면 경쟁이 낮은 체험단부터 보여줘요") */
export function tieBreakLabel(sort: SortOption, hasRateFilter: boolean, dirs?: Partial<SortDirs>): string {
  const [primary, second] = sortChain(sort, hasRateFilter);
  return `${SORT_KEY_SAME[primary]} ${SORT_KEY_FIRST[second][dirOf(dirs, second)]} 체험단부터 보여줘요`;
}

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
  /** 기준별 방향 (없으면 DEFAULT_SORT_DIRS) */
  sortDirs?: Partial<SortDirs>;
}

/** 체험단 플랫폼 — scraper/connectors/__init__.py REGISTRY의 label과 같은 순서로 맞춘다. */
export const PLATFORMS = ["레뷰", "파블로", "리뷰노트", "서울오빠", "디너의여왕", "모두블로그"] as const;

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
  const columns: Record<SortOption, string> = {
    deadline: "deadline_date",
    competition: "apply_rate",
    recruit: "recruit_count",
    latest: "created_at",
  };
  for (const key of sortChain(filters.sort ?? "deadline", Boolean(filters.applyRate))) {
    query = query.order(columns[key], { ascending: dirOf(filters.sortDirs, key) === "asc", nullsFirst: false });
  }
  // 마지막은 id — 같은 배치로 들어온 행은 created_at이 같아서 id로 순서를 고정해야
  // 페이지 경계에서 행이 겹치거나 빠지지 않는다
  query = query.order("id");

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
  /** 모집 중인 체험단의 최대 경쟁률 (N:1의 N, 올림) — 경쟁률 슬라이더의 오른쪽 끝 */
  maxApplyRate: number;
}

/**
 * 필터 선택지. DB 함수 campaign_filter_options()가 모집 중 캠페인 전체를 집계해 준다
 * (예전처럼 행을 받아 세면 PostgREST 기본 한도 1,000행까지만 보여서 일부 지역·분류가 빠졌다).
 */
export async function fetchFilterOptions(): Promise<FilterOptions> {
  const { data, error } = await supabase.rpc("campaign_filter_options");
  if (error) throw error;
  const raw = (data ?? {}) as {
    sidos?: string[];
    guguns?: Record<string, { name: string; count: number }[]>;
    categories?: string[];
    types?: string[];
    channels?: string[];
    maxApplyRate?: number | string;
  };

  // 실제 데이터에 있는 값만 보여주되, 순서는 정의된 표준 순서를 따른다.
  const byOrder = (order: string[]) => (a: string, b: string) => {
    const rank = (v: string) => (order.indexOf(v) === -1 ? order.length : order.indexOf(v));
    return rank(a) - rank(b) || a.localeCompare(b);
  };
  return {
    sidos: [...(raw.sidos ?? [])].sort(byOrder(SIDO_ORDER)),
    guguns: raw.guguns ?? {},
    categories: [...(raw.categories ?? [])].sort(byOrder(CATEGORIES.map((c) => c.label))),
    types: (raw.types ?? []).filter((t) => t in CAMPAIGN_TYPE_LABELS).sort(byOrder(Object.keys(CAMPAIGN_TYPE_LABELS))),
    channels: (raw.channels ?? [])
      .filter((c) => c in REVIEW_CHANNEL_LABELS)
      .sort(byOrder(Object.keys(REVIEW_CHANNEL_LABELS))),
    maxApplyRate: Math.max(Number(raw.maxApplyRate) || DEFAULT_MAX_APPLY_RATE, 2),
  };
}

/** 집계를 아직 못 받았을 때 경쟁률 슬라이더의 끝 */
export const DEFAULT_MAX_APPLY_RATE = 10;

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
export function dDay(deadlineDate: string | null, today: string = todayKst()): number | null {
  if (!deadlineDate) return null;
  // 두 날짜를 모두 UTC 자정으로 놓고 빼면 기기 시간대·서머타임 영향 없이 날짜 차이만 남는다
  const toUtc = (ymd: string) => {
    const [y, m, d] = ymd.slice(0, 10).split("-").map(Number);
    return Date.UTC(y, m - 1, d);
  };
  return Math.round((toUtc(deadlineDate) - toUtc(today)) / 86400000);
}


// ---- 서버 경로(/api/...)와 주고받는 필터 직렬화 ---------------------------------------------------

const SORT_VALUES: SortOption[] = ["deadline", "latest", "competition", "recruit"];

function cleanList(value: unknown, maxItems = 40, maxLen = 40): string[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const items = value.filter((v): v is string => typeof v === "string" && v.length > 0 && v.length <= maxLen);
  return items.length > 0 ? [...new Set(items)].slice(0, maxItems).sort() : undefined;
}

/**
 * 필터를 URL에 실을 문자열로. 같은 조건은 항상 같은 문자열이 되게(키 순서·배열 순서 고정) 해서
 * CDN/서버 캐시가 같은 요청으로 알아보게 한다. 관심 목록(ids)은 기기마다 달라서 싣지 않는다.
 */
export function encodeFilters(filters: CampaignFilters): string {
  const out: Record<string, unknown> = {};
  if (filters.search) out.q = filters.search.slice(0, 60);
  for (const key of ["sidos", "guguns", "categories", "platforms", "types", "channels"] as const) {
    const list = cleanList(filters[key]);
    if (list) out[key] = list;
  }
  if (filters.applyRate) {
    // JSON은 Infinity를 못 담아서 "상한 없음"은 null로
    out.rate = [filters.applyRate.min, Number.isFinite(filters.applyRate.max) ? filters.applyRate.max : null];
  }
  if (filters.includeOpenEnded === false) out.open = 0;
  if (filters.sort) out.sort = filters.sort;
  // 기본과 다른 방향만 싣는다 — 기본 정렬의 캐시 키가 예전과 같게
  const dirs = SORT_VALUES.filter((k) => dirOf(filters.sortDirs, k) !== DEFAULT_SORT_DIRS[k]).map(
    (k) => `${k}:${dirOf(filters.sortDirs, k)}`
  );
  if (dirs.length > 0) out.dirs = dirs;
  return JSON.stringify(out);
}

/** encodeFilters의 반대. 낯선 값은 버리고, 형식이 틀리면 null — 서버 경로가 임의 입력을 DB로 넘기지 않게 한다. */
export function parseFilters(raw: string | null): CampaignFilters | null {
  if (!raw || raw.length > 4000) return null;
  let data: Record<string, unknown>;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return null;
    data = parsed as Record<string, unknown>;
  } catch {
    return null;
  }
  const filters: CampaignFilters = {};
  if (typeof data.q === "string" && data.q.trim()) filters.search = data.q.trim().slice(0, 60);
  for (const key of ["sidos", "guguns", "categories", "platforms", "types", "channels"] as const) {
    const list = cleanList(data[key]);
    if (list) filters[key] = list;
  }
  if (Array.isArray(data.rate) && typeof data.rate[0] === "number") {
    const max = typeof data.rate[1] === "number" ? data.rate[1] : Infinity;
    filters.applyRate = { min: Math.max(0, data.rate[0]), max };
  }
  if (data.open === 0) filters.includeOpenEnded = false;
  if (typeof data.sort === "string" && (SORT_VALUES as string[]).includes(data.sort)) filters.sort = data.sort as SortOption;
  if (Array.isArray(data.dirs)) {
    const dirs: Partial<SortDirs> = {};
    for (const item of data.dirs.slice(0, 4)) {
      const [key, dir] = typeof item === "string" ? item.split(":") : [];
      if ((SORT_VALUES as string[]).includes(key) && (dir === "asc" || dir === "desc")) dirs[key as SortOption] = dir;
    }
    if (Object.keys(dirs).length > 0) filters.sortDirs = dirs;
  }
  return filters;
}
