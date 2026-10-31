"use client";

import { ArrowUpDownIcon, ChevronDownIcon, SlidersHorizontalIcon, StarIcon, XIcon } from "lucide-react";
import { cn } from "cn";
import { activeFilterCount, type FilterSection, type FilterState } from "@/components/filter-sheet";
import { CAMPAIGN_TYPE_LABELS, REVIEW_CHANNEL_LABELS, SORT_OPTIONS } from "@/lib/campaigns";

function multiLabel(fallback: string, items: string[], format: (v: string) => string = (v) => v) {
  if (items.length === 0) return fallback;
  if (items.length === 1) return format(items[0]);
  return `${format(items[0])} 외 ${items.length - 1}`;
}

function formatApplyRateLabel(range: FilterState["applyRate"]) {
  if (!range) return "경쟁률";
  const n = (v: number) => Math.round(v * 10) / 10;
  if (range.max === Infinity) return `경쟁률 ${n(range.min)}:1+`;
  return `경쟁률 ${n(range.min)}~${n(range.max)}:1`;
}

/** 검색창 아래 필터 줄: [필터 n] [★ 관심] [체험 방식] [지역] [카테고리] … */
export function QuickFilters({
  value,
  favoriteCount,
  onOpenSection,
  onToggleFavorites,
}: {
  value: FilterState;
  favoriteCount: number;
  onOpenSection: (section: FilterSection) => void;
  onToggleFavorites: () => void;
}) {
  const count = activeFilterCount(value);

  return (
    <div className="flex items-center gap-2 overflow-x-auto px-4 py-2.5 [scrollbar-width:none]">
      <Chip active={count > 0} onClick={() => onOpenSection("type")} ariaLabel={`필터 ${count}개 적용됨`}>
        <SlidersHorizontalIcon className="size-3.5" />
        필터
        {count > 0 && (
          <span className="flex size-4.5 items-center justify-center rounded-full bg-primary-foreground text-[11px] font-semibold tabular-nums text-primary">
            {count}
          </span>
        )}
      </Chip>
      <Chip active={value.favoritesOnly} onClick={onToggleFavorites}>
        <StarIcon className={cn("size-3.5", value.favoritesOnly && "fill-current")} />
        관심
        {favoriteCount > 0 && <span className="tabular-nums">{favoriteCount}</span>}
      </Chip>
      <span className="h-5 w-px shrink-0 bg-border" aria-hidden />
      <Chip active={value.types.length > 0} onClick={() => onOpenSection("type")}>
        {multiLabel("체험 방식", value.types, (t) => CAMPAIGN_TYPE_LABELS[t]?.label ?? t)}
        <ChevronDownIcon className="size-3.5" />
      </Chip>
      <Chip active={value.sidos.length + value.guguns.length > 0} onClick={() => onOpenSection("region")}>
        {multiLabel("지역", [...value.sidos, ...value.guguns], (r) => r.split(" ").pop()!)}
        <ChevronDownIcon className="size-3.5" />
      </Chip>
      <Chip active={value.categories.length > 0} onClick={() => onOpenSection("category")}>
        {multiLabel("카테고리", value.categories)}
        <ChevronDownIcon className="size-3.5" />
      </Chip>
      <Chip active={value.channels.length > 0} onClick={() => onOpenSection("channel")}>
        {multiLabel("리뷰 채널", value.channels, (c) => REVIEW_CHANNEL_LABELS[c] ?? c)}
        <ChevronDownIcon className="size-3.5" />
      </Chip>
      <Chip active={value.applyRate !== null} onClick={() => onOpenSection("applyRate")}>
        {formatApplyRateLabel(value.applyRate)}
        <ChevronDownIcon className="size-3.5" />
      </Chip>
      <Chip active={value.platforms.length > 0} onClick={() => onOpenSection("platform")}>
        {multiLabel("사이트", value.platforms)}
        <ChevronDownIcon className="size-3.5" />
      </Chip>
    </div>
  );
}

/** 목록 바로 위: "총 N개" 요약 + 정렬. 정렬이 무엇인지 항상 글자로 보이게 한다. */
export function ResultsBar({
  total,
  loading,
  value,
  onOpenSort,
  onToggleOpenEnded,
  onReset,
}: {
  total: number;
  loading: boolean;
  value: FilterState;
  onOpenSort: () => void;
  onToggleOpenEnded: () => void;
  onReset: () => void;
}) {
  const sortLabel = SORT_OPTIONS.find((o) => o.value === value.sort)?.label ?? "정렬";
  const filtered = activeFilterCount(value) > 0 || value.favoritesOnly;

  return (
    <div className="flex items-center justify-between gap-2 border-y border-border bg-muted/40 px-4 py-2">
      <div className="flex min-w-0 items-center gap-2 text-sm">
        <span className="text-muted-foreground">
          {value.favoritesOnly ? "관심 " : "총 "}
          <b className="font-semibold tabular-nums text-foreground">{loading ? "–" : total.toLocaleString()}</b>개
        </span>
        {filtered && (
          <button
            onClick={onReset}
            className="flex items-center gap-0.5 text-xs text-muted-foreground underline-offset-2 hover:underline"
          >
            <XIcon className="size-3" />
            조건 지우기
          </button>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-1">
      {value.sort === "deadline" && (
        <button
          role="switch"
          aria-checked={value.includeOpenEnded}
          onClick={onToggleOpenEnded}
          className={cn(
            "flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs transition-colors focus-visible:outline-2 focus-visible:outline-ring",
            value.includeOpenEnded
              ? "border-border text-muted-foreground"
              : "border-primary bg-primary/10 font-medium text-primary"
          )}
        >
          {value.includeOpenEnded ? "상시모집 포함" : "상시모집 제외"}
        </button>
      )}
      <button
        onClick={onOpenSort}
        aria-label={`정렬: ${sortLabel}. 눌러서 바꾸기`}
        className="flex shrink-0 items-center gap-1 rounded-md px-1.5 py-1 text-sm font-medium text-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
      >
        <ArrowUpDownIcon className="size-3.5 text-muted-foreground" />
        {sortLabel}
      </button>
      </div>
    </div>
  );
}

function Chip({
  active,
  onClick,
  ariaLabel,
  children,
}: {
  active?: boolean;
  onClick: () => void;
  ariaLabel?: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      aria-label={ariaLabel}
      aria-pressed={active}
      className={cn(
        "flex shrink-0 items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
        active && "border-primary bg-primary text-primary-foreground"
      )}
    >
      {children}
    </button>
  );
}
