"use client";

import { ChevronDownIcon, ZapIcon } from "lucide-react";
import { cn } from "cn";
import type { FilterState } from "@/components/filter-sheet";

export function QuickFilters({
  value,
  onOpenTab,
  onToggleSort,
}: {
  value: FilterState;
  onOpenTab: (tab: "region" | "category") => void;
  onToggleSort: () => void;
}) {
  const regionLabel =
    value.sidos.length === 0
      ? "지역 전체"
      : value.sidos.length === 1
        ? value.sidos[0]
        : `${value.sidos[0]} 외 ${value.sidos.length - 1}`;

  const categoryLabel =
    value.categories.length === 0
      ? "카테고리"
      : value.categories.length === 1
        ? value.categories[0]
        : `${value.categories[0]} 외 ${value.categories.length - 1}`;

  return (
    <div className="flex items-center gap-2 overflow-x-auto border-b border-border px-4 py-2.5">
      <Chip onClick={() => onOpenTab("region")}>
        {regionLabel}
        <ChevronDownIcon className="size-3.5" />
      </Chip>
      <Chip onClick={() => onOpenTab("category")}>
        {categoryLabel}
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
