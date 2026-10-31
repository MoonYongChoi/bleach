"use client";

import { SearchIcon, XIcon } from "lucide-react";
import { Input } from "@/components/ui/input";

/** 로고의 푸른 물방울은 "빨래 푸르름" — 흰 빨래를 더 희게 보이게 하는 한 방울에서 따왔다 */
function Wordmark() {
  return (
    <div className="flex shrink-0 items-center gap-1.5" aria-label="BLEACH, 블로그 체험단 서치">
      <svg viewBox="0 0 16 20" className="h-5 w-4 text-primary" aria-hidden>
        <path d="M8 1C8 1 1.5 8.4 1.5 12.6A6.5 6.5 0 0 0 14.5 12.6C14.5 8.4 8 1 8 1Z" fill="currentColor" />
        <path d="M5 12.8a3.2 3.2 0 0 0 2.6 3.1" stroke="white" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity=".8" />
      </svg>
      <span className="font-display text-[21px] font-extrabold leading-none tracking-[-0.04em] text-foreground">
        bleach
      </span>
    </div>
  );
}

export function SiteHeader({
  search,
  onSearchChange,
}: {
  search: string;
  onSearchChange: (value: string) => void;
}) {
  return (
    <header className="flex items-center gap-3 px-4 pt-3 pb-2">
      <Wordmark />
      <div className="group relative flex-1">
        <SearchIcon className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-primary" />
        <Input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="체험단 검색"
          aria-label="체험단 검색"
          className="h-10 rounded-full border-transparent bg-muted pl-10 pr-9 text-sm shadow-none transition-[background-color,box-shadow] duration-200 placeholder:text-muted-foreground focus-visible:bg-card focus-visible:ring-2 focus-visible:ring-primary/40"
        />
        {search && (
          <button
            onClick={() => onSearchChange("")}
            aria-label="검색어 지우기"
            className="badge-pop absolute right-1.5 top-1/2 flex size-7 -translate-y-1/2 items-center justify-center rounded-full text-muted-foreground hover:bg-border"
          >
            <XIcon className="size-3.5" />
          </button>
        )}
      </div>
    </header>
  );
}
