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
import { Slider } from "@/components/ui/slider";
import { PLATFORMS, type ApplyRateRange, type SortOption } from "@/lib/campaigns";
import { cn } from "cn";

type Tab = "region" | "category" | "platform" | "applyRate" | "sort";

export interface FilterState {
  sidos: string[];
  categories: string[];
  platforms: string[];
  applyRate: ApplyRateRange | null;
  sort: SortOption;
}

export const EMPTY_FILTER_STATE: FilterState = {
  sidos: [],
  categories: [],
  platforms: [],
  applyRate: null,
  sort: "latest",
};

// 지원률 슬라이더 범위: 0~200%. 오른쪽 끝(2)에 두면 "200% 이상"까지 무제한으로 연다.
const APPLY_RATE_SLIDER_MAX = 2;

function formatRate(value: number) {
  return value >= APPLY_RATE_SLIDER_MAX ? `${Math.round(value * 100)}%+` : `${Math.round(value * 100)}%`;
}

export function FilterSheet({
  open,
  onOpenChange,
  initialTab,
  sidoOptions,
  categoryOptions,
  value,
  onApply,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialTab: Tab;
  sidoOptions: string[];
  categoryOptions: string[];
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

  const sliderValue: [number, number] = draft.applyRate
    ? [draft.applyRate.min, Math.min(draft.applyRate.max, APPLY_RATE_SLIDER_MAX)]
    : [0, APPLY_RATE_SLIDER_MAX];

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
              ["platform", "업체"],
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

          {tab === "platform" && (
            <div>
              <p className="mb-2 text-xs text-muted-foreground">체험단 업체 (복수 선택 가능)</p>
              <div className="flex flex-wrap gap-2">
                {PLATFORMS.map((platform) => (
                  <ChipButton
                    key={platform}
                    active={draft.platforms.includes(platform)}
                    onClick={() =>
                      setDraft((d) => ({ ...d, platforms: toggle(d.platforms, platform) }))
                    }
                  >
                    {platform}
                  </ChipButton>
                ))}
              </div>
            </div>
          )}

          {tab === "applyRate" && (
            <div className="flex flex-col gap-4">
              <p className="text-xs text-muted-foreground">
                지원률 = 현재 신청인원 ÷ 모집인원 (데이터가 있는 체험단만 대상). 바를 드래그해서
                범위를 고르세요.
              </p>
              <div className="flex items-center justify-between text-sm font-semibold text-foreground">
                <span>{formatRate(sliderValue[0])}</span>
                <span>{formatRate(sliderValue[1])}</span>
              </div>
              <Slider
                min={0}
                max={APPLY_RATE_SLIDER_MAX}
                step={0.05}
                minStepsBetweenValues={1}
                value={sliderValue}
                onValueChange={(next) => {
                  const [min, max] = next as number[];
                  setDraft((d) => ({
                    ...d,
                    applyRate: { min, max: max >= APPLY_RATE_SLIDER_MAX ? Infinity : max },
                  }));
                }}
              />
              {draft.applyRate && (
                <button
                  onClick={() => setDraft((d) => ({ ...d, applyRate: null }))}
                  className="self-start text-xs text-muted-foreground underline underline-offset-2"
                >
                  전체로 초기화
                </button>
              )}
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
