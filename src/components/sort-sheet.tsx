"use client";

import { CheckIcon } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { SORT_OPTIONS, type SortOption } from "@/lib/campaigns";
import { cn } from "cn";

/** 정렬은 결과를 줄이지 않으니 필터와 분리하고, 고르는 즉시 적용한다 (적용 버튼 없음). */
export function SortSheet({
  open,
  onOpenChange,
  value,
  onChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  value: SortOption;
  onChange: (next: SortOption) => void;
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="mx-auto max-w-md gap-0 rounded-t-2xl pb-[env(safe-area-inset-bottom)]">
        <SheetHeader className="pb-2">
          <SheetTitle>정렬</SheetTitle>
        </SheetHeader>
        <ul role="radiogroup" aria-label="정렬 기준" className="flex flex-col px-2 pb-3">
          {SORT_OPTIONS.map((option) => {
            const selected = option.value === value;
            return (
              <li key={option.value}>
                <button
                  role="radio"
                  aria-checked={selected}
                  onClick={() => {
                    onChange(option.value);
                    onOpenChange(false);
                  }}
                  className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left hover:bg-muted/60 focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className={cn("text-[15px] text-foreground", selected && "font-semibold text-primary")}>
                      {option.label}
                    </span>
                    <span className="text-xs text-muted-foreground">{option.hint}</span>
                  </span>
                  {selected && <CheckIcon className="size-5 shrink-0 text-primary" />}
                </button>
              </li>
            );
          })}
        </ul>
      </SheetContent>
    </Sheet>
  );
}
