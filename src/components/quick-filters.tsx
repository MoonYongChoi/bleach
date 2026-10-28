"use client";

import { ChevronDownIcon, ZapIcon } from "lucide-react";
import { cn } from "cn";
import type { FilterState } from "@/components/filter-sheet";

function multiLabel(fallback: string, items: string[]) {
  if (items.length === 0) return fallback;
  if (items.length === 1) return items[0];
  return `${items[0]} 외 ${items.length - 1}`;
}

const APPLY_RATE_LABELS: Record<string, string> = {
  "0:0.3": "지원률 30% 미만",
  "0.3:1": "지원률 30~100%",
  "1:Infinity": "지원률 100%+",
};

export function QuickFilters({
  value,
  onOpenTab,
  onToggleSort,
}: {
  value: FilterState;
  onOpenTab: (tab: "region" | "category" | "vendor" | "applyRate") => void;
  onToggleSort: () => void;
}) {
  const applyRateLabel = value.applyRate
    ? (APPLY_RATE_LABELS[`${value.applyRate.min}:${value.applyRate.max}`] ?? "지원률")
    : "지원률";

  return (
    <div className="flex items-center gap-2 overflow-x-auto border-b border-border px-4 py-2.5">
      <Chip onClick={() => onOpenTab("region")}>
        {multiLabel("지역 전체", value.sidos)}
        <ChevronDownIcon className="size-3.5" />
      </Chip>
      <Chip onClick={() => onOpenTab("category")}>
        {multiLabel("카테고리", value.categories)}
        <ChevronDownIcon className="size-3.5" />
      </Chip>
      <Chip onClick={() => onOpenTab("vendor")}>
        {multiLabel("업체", value.vendors)}
        <ChevronDownIcon className="size-3.5" />
      </Chip>
      <Chip active={value.applyRate !== null} onClick={() => onOpenTab("applyRate")}>
        {applyRateLabel}
        <ChevronDownIcon className="size-3.5" />
      </Chip>
      <Chip active={value.sort === "deadline"} onClick={onToggleSort}>
        <ZapIcon className="size-3.5" />
        마감임박순
      </Chip>
    </div>
  );
}

function Chip({
  active,
  onClick,
  children,
}: {
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex shrink-0 items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm font-medium text-foreground transition-colors",
        active && "border-primary bg-primary text-primary-foreground"
      )}
    >
      {children}
    </button>
  );
}
