"use client";

import { CheckIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { SORT_CRITERIA, tieBreakLabel, type SortDir, type SortDirs, type SortOption } from "@/lib/campaigns";
import { cn } from "cn";

/**
 * 정렬: 기준(마감·경쟁·모집인원·등록일)마다 방향을 고를 수 있고, 마지막으로 누른 기준이 1순위가 된다.
 * 나머지 기준은 고른 방향대로 같은 순위끼리의 순서에 쓰인다. 누르는 즉시 목록에 반영하고, 시트는 열어 둔다.
 */
export function SortSheet({
  open,
  onOpenChange,
  value,
  dirs,
  onChange,
  includeOpenEnded,
  onToggleOpenEnded,
  hasRateFilter,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  value: SortOption;
  dirs: SortDirs;
  onChange: (sort: SortOption, dirs: SortDirs) => void;
  includeOpenEnded: boolean;
  onToggleOpenEnded: () => void;
  /** 경쟁률 필터가 걸려 있으면 같은 순위 안에서 경쟁률이 먼저 온다 */
  hasRateFilter: boolean;
}) {
  const choose = (sort: SortOption, dir?: SortDir) => onChange(sort, dir ? { ...dirs, [sort]: dir } : dirs);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="bottom" className="mx-auto max-w-md gap-0 rounded-t-2xl pb-[env(safe-area-inset-bottom)]">
        <SheetHeader className="pb-1">
          <SheetTitle>정렬</SheetTitle>
          <p className="text-xs text-muted-foreground">기준을 누르면 그 기준이 가장 먼저 적용돼요</p>
        </SheetHeader>
        <ul role="radiogroup" aria-label="가장 먼저 적용할 정렬 기준" className="flex flex-col gap-1 px-2 pb-2">
          {SORT_CRITERIA.map((c) => {
            const selected = c.value === value;
            return (
              <li key={c.value}>
                <div
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors",
                    selected ? "bg-primary/8" : "hover:bg-muted/60"
                  )}
                >
                  <button
                    role="radio"
                    aria-checked={selected}
                    onClick={() => choose(c.value)}
                    className="flex min-w-0 flex-1 items-center gap-2 text-left focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    <span
                      className={cn(
                        "flex size-5 shrink-0 items-center justify-center rounded-full border",
                        selected ? "border-primary bg-primary text-primary-foreground" : "border-border"
                      )}
                    >
                      {selected && <CheckIcon className="size-3.5" strokeWidth={3} />}
                    </span>
                    <span className={cn("text-[15px] text-foreground", selected && "font-semibold text-primary")}>
                      {c.title}
                    </span>
                  </button>
                  <div role="group" aria-label={`${c.title} 방향`} className="flex shrink-0 rounded-lg bg-muted p-0.5">
                    {c.dirs.map((d) => {
                      const on = dirs[c.value] === d.dir;
                      return (
                        <button
                          key={d.dir}
                          aria-pressed={on}
                          onClick={() => choose(c.value, d.dir)}
                          className={cn(
                            "min-w-14 rounded-md px-3 py-1.5 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-ring",
                            on ? "bg-card font-semibold text-foreground shadow-sm" : "text-muted-foreground"
                          )}
                        >
                          {d.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
                {c.value === "deadline" && selected && (
                  <div className="mx-3 mb-1 mt-1 flex items-center justify-between rounded-lg bg-muted/60 px-3 py-2.5">
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
        <p className="px-5 pb-3 text-xs text-muted-foreground">{tieBreakLabel(value, hasRateFilter, dirs)}</p>
        <div className="border-t border-border px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
          <Button className="w-full" onClick={() => onOpenChange(false)}>
            확인
          </Button>
        </div>
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
