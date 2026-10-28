"use client";

import { SearchIcon } from "lucide-react";
import { Input } from "@/components/ui/input";

export function SiteHeader({
  search,
  onSearchChange,
}: {
  search: string;
  onSearchChange: (value: string) => void;
}) {
  return (
    <header className="flex items-center gap-3 border-b border-border px-4 py-3">
      <div className="flex shrink-0 flex-col leading-none">
        <span className="text-lg font-extrabold tracking-tight text-primary">BLEACH</span>
        <span className="text-[10px] text-muted-foreground">블로그 체험단 서치</span>
      </div>
      <div className="relative flex-1">
        <SearchIcon className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="블로그 체험단 검색"
          className="pl-8"
        />
      </div>
    </header>
  );
}
