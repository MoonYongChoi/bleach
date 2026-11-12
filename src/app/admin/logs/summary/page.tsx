import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { connection } from "next/server";
import { supabase } from "@/lib/supabase";
import { cn } from "cn";

export const metadata: Metadata = {
  title: "이용 기록 요약 — bleach admin",
  robots: { index: false, follow: false },
};

type Daily = { day: string; visitors: number; page_views: number; searches: number; filters: number; clicks: number };
type Top = { label: string; n: number };
type Recent = {
  ts: string;
  event: "page_view" | "search" | "filter" | "click";
  session: string;
  path: string | null;
  referrer: string | null;
  device: string | null;
  data: Record<string, unknown>;
};

const EVENT_LABELS: Record<Recent["event"], string> = { page_view: "방문", search: "검색", filter: "필터", click: "클릭" };

const KST = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});
function kst(iso: string): string {
  const p = Object.fromEntries(KST.formatToParts(new Date(iso)).map((x) => [x.type, x.value]));
  return `${p.month}-${p.day} ${p.hour}:${p.minute}`;
}

export default function LogsPage() {
  return (
    <div className="mx-auto w-full max-w-3xl flex-1 bg-card px-4 py-6 sm:px-6">
      <div className="flex items-baseline justify-between gap-3">
        <h1 className="text-xl font-bold tracking-tight text-foreground">이용 기록 요약</h1>
        <span className="flex gap-3 text-sm">
          <Link href="/admin/logs" className="text-primary hover:underline">
            원본 기록 →
          </Link>
          <Link href="/admin" className="text-primary hover:underline">
            수집 현황 →
          </Link>
        </span>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        방문자 = 브라우저 탭 수(로그인·쿠키 없이 탭마다 새 값). 시각은 한국 시간, 기록은 90일 보관.
      </p>
      <Suspense fallback={<p className="mt-8 text-sm text-muted-foreground">불러오는 중…</p>}>
        <LogsData />
      </Suspense>
    </div>
  );
}

async function top(kind: string, days = 7, limit = 15): Promise<Top[]> {
  const { data } = await supabase.rpc("admin_log_top", { p_kind: kind, p_days: days, p_limit: limit });
  return (data ?? []) as Top[];
}

async function LogsData() {
  await connection(); // 열 때마다 최신 값

  const [daily, recent, referrers, searches, filters, platforms, campaigns, devices] = await Promise.all([
    supabase.rpc("admin_log_daily", { p_days: 30 }),
    supabase.rpc("admin_log_recent", { p_limit: 60 }),
    top("referrer"),
    top("search"),
    top("filter"),
    top("click_platform"),
    top("click_campaign"),
    top("device"),
  ]);
  if (daily.error) {
    return <p className="mt-8 text-sm text-coral">기록을 불러오지 못했습니다: {daily.error.message}</p>;
  }
  const days = (daily.data ?? []) as Daily[];
  const maxViews = Math.max(1, ...days.map((d) => d.page_views));

  return (
    <>
      <Section title="최근 30일">
        {days.length === 0 ? (
          <Empty />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className={TH}>날짜</th>
                <th className={cn(TH, "text-right")}>방문자</th>
                <th className={cn(TH, "w-1/3")}>페이지뷰</th>
                <th className={cn(TH, "text-right")}>검색</th>
                <th className={cn(TH, "text-right")}>필터</th>
                <th className={cn(TH, "text-right")}>클릭</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {days.map((d) => (
                <tr key={d.day}>
                  <td className={cn(TD, "font-medium")}>{d.day.slice(5)}</td>
                  <td className={cn(TD, "text-right")}>{d.visitors.toLocaleString()}</td>
                  <td className={TD}>
                    <div className="flex items-center gap-2">
                      <span className="h-2 rounded-full bg-primary/70" style={{ width: `${(d.page_views / maxViews) * 100}%` }} />
                      <span className="text-xs text-muted-foreground">{d.page_views.toLocaleString()}</span>
                    </div>
                  </td>
                  <td className={cn(TD, "text-right")}>{d.searches.toLocaleString()}</td>
                  <td className={cn(TD, "text-right")}>{d.filters.toLocaleString()}</td>
                  <td className={cn(TD, "text-right font-medium")}>{d.clicks.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <div className="grid gap-x-6 sm:grid-cols-2">
        <TopList title="많이 누른 사이트 (7일)" rows={platforms} />
        <TopList title="유입 경로 (7일)" rows={referrers} />
        <TopList title="많이 누른 체험단 (7일)" rows={campaigns} />
        <TopList title="검색어 (7일)" rows={searches} />
        <TopList title="많이 쓴 필터·정렬 (7일)" rows={filters} />
        <TopList title="기기 (7일)" rows={devices} />
      </div>

      <Section title="최근 이벤트">
        {(recent.data ?? []).length === 0 ? (
          <Empty />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className={TH}>시각</th>
                <th className={TH}>종류</th>
                <th className={TH}>내용</th>
                <th className={TH}>탭</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {((recent.data ?? []) as Recent[]).map((r, i) => (
                <tr key={`${r.ts}-${i}`}>
                  <td className={cn(TD, "text-muted-foreground")}>{kst(r.ts)}</td>
                  <td className={TD}>{EVENT_LABELS[r.event] ?? r.event}</td>
                  <td className={cn(TD, "max-w-72 truncate")}>{describe(r)}</td>
                  <td className={cn(TD, "font-mono text-xs text-muted-foreground")}>{r.session}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
    </>
  );
}

function describe(r: Recent): string {
  const d = r.data ?? {};
  if (r.event === "search") return String(d.q ?? "");
  if (r.event === "filter") return String(d.summary ?? "");
  if (r.event === "click") return `${d.platform ?? ""} · ${d.title ?? ""}`;
  return [r.path, r.referrer && `← ${r.referrer}`, r.device].filter(Boolean).join(" ");
}

const TH = "whitespace-nowrap px-3 py-2 text-left text-xs font-medium text-muted-foreground";
const TD = "whitespace-nowrap px-3 py-2 tabular-nums";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="text-[15px] font-semibold text-foreground">{title}</h2>
      <div className="mt-3 overflow-x-auto rounded-xl border border-border">{children}</div>
    </section>
  );
}

function TopList({ title, rows }: { title: string; rows: Top[] }) {
  const max = Math.max(1, ...rows.map((r) => r.n));
  return (
    <Section title={title}>
      {rows.length === 0 ? (
        <Empty />
      ) : (
        <ul className="divide-y divide-border text-sm">
          {rows.map((r) => (
            <li key={r.label} className="relative flex items-center justify-between gap-3 px-3 py-2">
              <span
                className="absolute inset-y-1 left-0 rounded-r bg-primary/8"
                style={{ width: `${(r.n / max) * 100}%` }}
                aria-hidden
              />
              <span className="relative min-w-0 truncate">{r.label}</span>
              <span className="relative shrink-0 tabular-nums text-muted-foreground">{r.n.toLocaleString()}</span>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function Empty() {
  return <p className="px-3 py-4 text-sm text-muted-foreground">아직 기록이 없습니다.</p>;
}
