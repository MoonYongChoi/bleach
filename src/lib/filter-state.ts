import type { ApplyRateRange, CampaignFilters, SortOption } from "@/lib/campaigns";

// 화면의 필터 상태와 기본값. 서버(첫 화면 미리 그리기)와 브라우저가 같은 기본 조건을 쓰도록 클라이언트 전용이 아닌 곳에 둔다.

export interface FilterState {
  types: string[];
  sidos: string[];
  /** "경기 하남시" 형태 — campaigns.ts gugunKey() */
  guguns: string[];
  categories: string[];
  channels: string[];
  platforms: string[];
  applyRate: ApplyRateRange | null;
  favoritesOnly: boolean;
  sort: SortOption;
  /** 마감임박순일 때 상시모집(마감일 없음)도 보여줄지 */
  includeOpenEnded: boolean;
}

export const EMPTY_FILTER_STATE: FilterState = {
  types: [],
  sidos: [],
  guguns: [],
  categories: [],
  channels: [],
  platforms: [],
  applyRate: null,
  favoritesOnly: false,
  sort: "deadline",
  includeOpenEnded: true,
};

export function toQuery(search: string, f: FilterState, favoriteIds: string[]): CampaignFilters {
  return {
    search,
    sidos: f.sidos,
    guguns: f.guguns,
    categories: f.categories,
    platforms: f.platforms,
    types: f.types,
    channels: f.channels,
    applyRate: f.applyRate ?? undefined,
    ids: f.favoritesOnly ? favoriteIds : undefined,
    sort: f.sort,
    includeOpenEnded: f.includeOpenEnded,
  };
}
