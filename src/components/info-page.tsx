import Link from "next/link";
import { ChevronLeftIcon } from "lucide-react";
import { SiteFooter } from "@/components/site-footer";

/** 소개·개인정보처리방침·문의 같은 글 페이지의 공통 틀 */
export function InfoPage({ title, updated, children }: { title: string; updated?: string; children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-md flex-1 flex-col bg-card sm:shadow-[0_0_0_1px_var(--border)]">
      <header className="flex items-center gap-1 border-b border-border px-2 py-3">
        <Link
          href="/"
          className="flex items-center gap-0.5 rounded-lg px-2 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <ChevronLeftIcon className="size-4" />
          체험단 목록
        </Link>
      </header>
      <main className="flex-1 px-5 py-6">
        <h1 className="text-xl font-bold tracking-tight text-foreground">{title}</h1>
        {updated && <p className="mt-1 text-xs text-muted-foreground">{updated}</p>}
        <div className="mt-6 flex flex-col gap-6 text-[14px] leading-relaxed text-foreground/90 [&_h2]:mb-2 [&_h2]:text-[15px] [&_h2]:font-semibold [&_h2]:text-foreground [&_li]:ml-4 [&_li]:list-disc [&_a]:text-primary [&_a]:underline">
          {children}
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
