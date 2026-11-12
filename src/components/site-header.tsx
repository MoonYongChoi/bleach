"use client";

import Link from "next/link";
import { SearchIcon, XIcon } from "lucide-react";
import { Input } from "@/components/ui/input";

/** 로고의 푸른 물방울은 "빨래 푸르름" — 흰 빨래를 더 희게 보이게 하는 한 방울에서 따왔다 */
function Wordmark({ onHome }: { onHome?: () => void }) {
  return (
    <Link
      href="/"
      aria-label="bleach 처음 화면으로"
      onClick={(e) => {
        // 이미 첫 페이지라 다시 불러오지 않고, 검색·필터·정렬을 처음 상태로 돌리고 맨 위로 올린다
        if (!onHome || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
        e.preventDefault();
        onHome();
      }}
      className="flex shrink-0 flex-col gap-1 rounded-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
    >
      <div className="flex items-center gap-1.5">
        <svg viewBox="0 0 16 20" className="h-5 w-4 text-primary" aria-hidden>
          <path d="M8 1C8 1 1.5 8.4 1.5 12.6A6.5 6.5 0 0 0 14.5 12.6C14.5 8.4 8 1 8 1Z" fill="currentColor" />
          <path d="M5 12.8a3.2 3.2 0 0 0 2.6 3.1" stroke="white" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity=".8" />
        </svg>
        <span className="font-display text-[21px] font-extrabold leading-none tracking-[-0.04em] text-foreground">
          bleach
        </span>
      </div>
      <span className="text-[10px] font-medium leading-none text-muted-foreground" aria-hidden>
        블로그 리뷰체험 서치
      </span>
    </Link>
  );
}

/** 입력 중에는 목록이 바뀌지 않고, 엔터(모바일은 키보드의 "검색")를 눌러야 검색된다. */
export function SiteHeader({
  draft,
  onDraftChange,
  onSubmit,
  onHome,
}: {
  draft: string;
  onDraftChange: (value: string) => void;
  onSubmit: (value: string) => void;
  /** 로고를 눌렀을 때 — 처음 화면 상태로 */
  onHome?: () => void;
}) {
  return (
    <header className="flex items-center gap-3 px-4 pt-3 pb-2">
      <Wordmark onHome={onHome} />
      <form
        role="search"
        className="group relative min-w-0 flex-1"
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit(draft.trim());
          (document.activeElement as HTMLElement | null)?.blur(); // 모바일 키보드를 내려서 결과가 바로 보이게
        }}
      >
        <SearchIcon className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground transition-colors group-focus-within:text-primary" />
        <Input
          type="search"
          enterKeyHint="search"
          value={draft}
          onChange={(e) => onDraftChange(e.target.value)}
          placeholder="체험단 검색"
          aria-label="체험단 검색"
          className="h-10 rounded-full border-transparent bg-muted pl-10 pr-9 text-base sm:text-sm [&::-webkit-search-cancel-button]:hidden shadow-none transition-[background-color,box-shadow] duration-200 placeholder:text-muted-foreground focus-visible:bg-card focus-visible:ring-2 focus-visible:ring-primary/40"
        />
        {draft && (
          <button
            type="button"
            onClick={() => {
              onDraftChange("");
              onSubmit("");
            }}
            aria-label="검색어 지우기"
            className="badge-pop absolute right-1.5 top-1/2 flex size-7 -translate-y-1/2 items-center justify-center rounded-full text-muted-foreground hover:bg-border"
          >
            <XIcon className="size-3.5" />
          </button>
        )}
      </form>
    </header>
  );
}
