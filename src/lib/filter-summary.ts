import { CAMPAIGN_TYPE_LABELS, REVIEW_CHANNEL_LABELS, sortLabel } from "@/lib/campaigns";
import type { FilterState } from "@/lib/filter-state";

/** 이용 기록용 한 줄 요약 (예: "마감 임박순 · 지역 서울 강남구 · 맛집 · 경쟁률 ~9:1") */
export function filterSummary(f: FilterState): string {
  const parts: string[] = [sortLabel(f.sort, f.sortDirs)];
  const regions = [...f.guguns, ...f.sidos.filter((s) => !f.guguns.some((g) => g.startsWith(`${s} `)))];
  if (regions.length) parts.push(`지역 ${regions.join(",")}`);
  if (f.categories.length) parts.push(f.categories.join(","));
  if (f.types.length) parts.push(f.types.map((t) => CAMPAIGN_TYPE_LABELS[t]?.label ?? t).join(","));
  if (f.channels.length) parts.push(f.channels.map((c) => REVIEW_CHANNEL_LABELS[c] ?? c).join(","));
  if (f.platforms.length) parts.push(f.platforms.join(","));
  if (f.applyRate) {
    const { min, max } = f.applyRate;
    parts.push(`경쟁률 ${min > 0 ? min : ""}~${Number.isFinite(max) ? `${max}:1` : ""}`);
  }
  if (f.favoritesOnly) parts.push("관심만");
  if (!f.includeOpenEnded) parts.push("상시 제외");
  return parts.join(" · ").slice(0, 300);
}
