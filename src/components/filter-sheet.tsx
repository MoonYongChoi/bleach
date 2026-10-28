"use client";

import { useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import type { SortOption } from "@/lib/campaigns";
import { cn } from "cn";

type Tab = "region" | "category" | "sort";

export interface FilterState {
  sidos: string[];
  categories: string[];
  sort: SortOption;
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

  function toggle(list: string[], item: string) {
    return list.includes(item) ? list.filter((v) => v !== item) : [...list, item];
  }

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        if (next) {
          setTab(initialTab);
          setDraft(value);
        }
        onOpenChange(next);
      }}
    >
      <SheetContent side="bottom" className="max-h-[80vh] overflow-y-auto rounded-t-2xl">
        <SheetHeader>
          <SheetTitle>필터</SheetTitle>
        </SheetHeader>

        <div className="flex gap-4 border-b border-border px-4 text-sm">
          {(
            [
              ["region", "지역"],
              ["category", "카테고리"],
              ["sort", "마감임박순"],
            ] as const
          ).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={cn(
                "border-b-2 border-transparent pb-2 font-medium text-muted-foreground",
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
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => setDraft({ sidos: [], categories: [], sort: "latest" })}
          >
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
