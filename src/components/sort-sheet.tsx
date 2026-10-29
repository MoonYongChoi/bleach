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
  includeOpenEnded,
  onToggleOpenEnded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  value: SortOption;
  onChange: (next: SortOption) => void;
  includeOpenEnded: boolean;
  onToggleOpenEnded: () => void;
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
                {option.value === "deadline" && selected && (
                  <div className="mx-3 mb-1 flex items-center justify-between rounded-lg bg-muted/60 px-3 py-2.5">
                    <span className="flex flex-col">
                      <span className="text-sm text-foreground">상시모집도 보기</span>
                      <span className="text-xs text-muted-foreground">마감일이 없는 체험단은 목록 맨 뒤에 나와요</span>
                    </span>
                    <Switch checked={includeOpenEnded} onClick={onToggleOpenEnded} label="상시모집도 보기" />
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </SheetContent>
    </Sheet>
  );
}

function Switch({ checked, onClick, label }: { checked: boolean; onClick: () => void; label: string }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={onClick}
      className={cn(
        "relative h-6 w-10 shrink-0 rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
        checked ? "bg-primary" : "bg-input"
      )}
    >
      <span
        className={cn(
          "absolute top-0.5 left-0.5 size-5 rounded-full bg-background shadow transition-transform motion-reduce:transition-none",
          checked && "translate-x-4"
        )}
      />
    </button>
  );
}
