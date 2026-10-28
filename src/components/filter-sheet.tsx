"use client";

import { useEffect, useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import type { ApplyRateRange, SortOption } from "@/lib/campaigns";
import { cn } from "cn";

type Tab = "region" | "category" | "vendor" | "applyRate" | "sort";

export interface FilterState {
  sidos: string[];
  categories: string[];
  vendors: string[];
  applyRate: ApplyRateRange | null;
  sort: SortOption;
}

export const EMPTY_FILTER_STATE: FilterState = {
  sidos: [],
  categories: [],
  vendors: [],
  applyRate: null,
  sort: "latest",
};

const APPLY_RATE_PRESETS: { label: string; range: ApplyRateRange }[] = [
  { label: "30% 미만 (여유)", range: { min: 0, max: 0.3 } },
  { label: "30~100%", range: { min: 0.3, max: 1 } },
  { label: "100% 이상 (경쟁 치열)", range: { min: 1, max: Infinity } },
];

function sameRange(a: ApplyRateRange | null, b: ApplyRateRange | null) {
  if (a === null || b === null) return a === b;
  return a.min === b.min && a.max === b.max;
}

export function FilterSheet({
  open,
  onOpenChange,
  initialTab,
  sidoOptions,
  categoryOptions,
  vendorOptions,
  value,
  onApply,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialTab: Tab;
  sidoOptions: string[];
  categoryOptions: string[];
  vendorOptions: string[];
  value: FilterState;
  onApply: (next: FilterState) => void;
}) {
  const [tab, setTab] = useState<Tab>(initialTab);
  const [draft, setDraft] = useState<FilterState>(value);

  // `open` is driven externally (quick-filter chips set it directly), so the
  // underlying dialog's onOpenChange never fires for that transition — sync here instead.
  useEffect(() => {
    if (open) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: reset the draft to match the chip that was clicked each time the sheet (re)opens
      setTab(initialTab);
      setDraft(value);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only re-sync on open/tab change, not every `value` edit
  }, [open, initialTab]);

  function toggle(list: string[], item: string) {
    return list.includes(item) ? list.filter((v) => v !== item) : [...list, item];
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="max-h-[80vh] overflow-y-auto rounded-t-2xl">
        <SheetHeader>
          <SheetTitle>필터</SheetTitle>
        </SheetHeader>

        <div className="flex gap-4 overflow-x-auto border-b border-border px-4 text-sm">
          {(
            [
              ["region", "지역"],
              ["category", "카테고리"],
              ["vendor", "업체"],
              ["applyRate", "지원률"],
              ["sort", "마감임박순"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={cn(
                "shrink-0 border-b-2 border-transparent pb-2 font-medium text-muted-foreground",
                tab === key && "border-foreground text-foreground"
              )}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-3">
          {tab === "region" && (
            <div>
              <p className="mb-2 text-xs text-muted-foreground">지역 (복수 선택 가능)</p>
              <div className="flex flex-wrap gap-2">
                {sidoOptions.map((sido) => (
                  <ChipButton
                    key={sido}
                    active={draft.sidos.includes(sido)}
                    onClick={() => setDraft((d) => ({ ...d, sidos: toggle(d.sidos, sido) }))}
                  >
                    {sido}
                  </ChipButton>
                ))}
              </div>
            </div>
          )}

          {tab === "category" && (
            <div>
              <p className="mb-2 text-xs text-muted-foreground">카테고리 (복수 선택 가능)</p>
              <div className="flex flex-wrap gap-2">
                {categoryOptions.map((category) => (
                  <ChipButton
                    key={category}
                    active={draft.categories.includes(category)}
                    onClick={() =>
                      setDraft((d) => ({ ...d, categories: toggle(d.categories, category) }))
                    }
                  >
                    {category}
                  </ChipButton>
                ))}
              </div>
            </div>
          )}

          {tab === "vendor" && (
            <div>
              <p className="mb-2 text-xs text-muted-foreground">
                체험단 업체 (복수 선택 가능 · 데이터가 있는 업체만 표시)
              </p>
              <div className="flex flex-wrap gap-2">
                {vendorOptions.length === 0 && (
                  <p className="text-sm text-muted-foreground">선택 가능한 업체 정보가 없어요</p>
                )}
                {vendorOptions.map((vendor) => (
                  <ChipButton
                    key={vendor}
                    active={draft.vendors.includes(vendor)}
                    onClick={() => setDraft((d) => ({ ...d, vendors: toggle(d.vendors, vendor) }))}
                  >
                    {vendor}
                  </ChipButton>
                ))}
              </div>
            </div>
          )}

          {tab === "applyRate" && (
            <div className="flex flex-col gap-2">
              <p className="mb-1 text-xs text-muted-foreground">
                지원률 = 현재 신청인원 ÷ 모집인원 (데이터가 있는 체험단만 대상)
              </p>
              <ChipButton
                full
                active={draft.applyRate === null}
                onClick={() => setDraft((d) => ({ ...d, applyRate: null }))}
              >
                전체
              </ChipButton>
              {APPLY_RATE_PRESETS.map((preset) => (
                <ChipButton
                  key={preset.label}
                  full
                  active={sameRange(draft.applyRate, preset.range)}
                  onClick={() => setDraft((d) => ({ ...d, applyRate: preset.range }))}
                >
                  {preset.label}
                </ChipButton>
              ))}
            </div>
          )}

          {tab === "sort" && (
            <div className="flex flex-col gap-2">
              {(
                [
                  ["latest", "최신순"],
                  ["deadline", "마감임박순"],
                ] as const
              ).map(([key, label]) => (
                <ChipButton
                  key={key}
                  full
                  active={draft.sort === key}
                  onClick={() => setDraft((d) => ({ ...d, sort: key }))}
                >
                  {label}
                </ChipButton>
              ))}
            </div>
          )}
        </div>

        <SheetFooter className="flex-row gap-2">
          <Button variant="outline" className="flex-1" onClick={() => setDraft(EMPTY_FILTER_STATE)}>
            초기화
          </Button>
          <Button
            className="flex-1"
            onClick={() => {
              onApply(draft);
              onOpenChange(false);
            }}
          >
            적용
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

function ChipButton({
  active,
  full,
  onClick,
  children,
}: {
  active: boolean;
  full?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-xl border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors",
        full && "w-full text-left",
        active && "border-primary bg-primary text-primary-foreground"
      )}
    >
      {children}
    </button>
  );
}
