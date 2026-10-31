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

  // 오른쪽 끝을 옅게 지워서 "옆으로 더 있다"는 걸 알려준다 (마지막 칩이 가려지지 않게 오른쪽 여백을 둔다)
  return (
    <div className="flex items-center gap-2 overflow-x-auto pr-10 pl-4 pt-1 pb-3 [scrollbar-width:none] [mask-image:linear-gradient(to_right,black_calc(100%-28px),transparent)]">
      <Chip active={count > 0} onClick={() => onOpenSection("type")} ariaLabel={`필터 ${count}개 적용됨`}>
        <SlidersHorizontalIcon className="size-3.5" />
        필터
        {count > 0 && (
          <span className="badge-pop flex size-4.5 items-center justify-center rounded-full bg-primary-foreground text-[11px] font-semibold tabular-nums text-primary">
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
    <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-0.5 bg-background px-4 py-1.5">
      <div className="flex min-w-0 items-center gap-2 whitespace-nowrap text-sm">
        <span className="text-muted-foreground">
          {value.favoritesOnly ? "관심 " : "총 "}
          <b
            key={loading ? "loading" : total}
            className="badge-pop inline-block font-display text-[15px] font-bold tabular-nums text-foreground"
          >
            {loading ? "–" : total.toLocaleString()}
          </b>
          개
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
      <div className="ml-auto flex shrink-0 items-center gap-1 whitespace-nowrap">
      {value.sort === "deadline" && (
        <button
          role="switch"
          aria-checked={value.includeOpenEnded}
          onClick={onToggleOpenEnded}
          className={cn(
            "relative flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs transition-colors duration-200 before:absolute before:-inset-y-2 before:-inset-x-1 before:content-[''] focus-visible:outline-2 focus-visible:outline-ring active:scale-95",
            value.includeOpenEnded
              ? "border-border bg-card text-muted-foreground"
              : "border-primary bg-primary/10 font-medium text-primary"
          )}
        >
          {value.includeOpenEnded ? "상시모집 포함" : "상시모집 제외"}
        </button>
      )}
      <button
        onClick={onOpenSort}
        aria-label={`정렬: ${sortLabel}. 눌러서 바꾸기`}
        className="flex shrink-0 items-center gap-1 rounded-lg px-2 py-1.5 text-sm font-semibold text-foreground transition-colors hover:bg-muted active:bg-border focus-visible:outline-2 focus-visible:outline-ring"
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
        "flex h-9 shrink-0 items-center gap-1 rounded-full border border-border bg-card px-3.5 text-sm font-medium text-foreground transition-[background-color,border-color,color,transform] duration-200 ease-out focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring active:scale-95",
        active && "border-primary bg-primary text-primary-foreground shadow-[0_2px_8px_-2px_rgb(43_71_240/0.45)]"
      )}
    >
      {children}
    </button>
  );
}
