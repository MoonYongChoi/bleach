import type { Metadata } from "next";
import { Suspense } from "react";
import { connection } from "next/server";
import { supabase } from "@/lib/supabase";
import { cn } from "cn";

export const metadata: Metadata = {
  title: "수집 현황 — bleach admin",
  robots: { index: false, follow: false },
};

type PlatformStatus = {
  platform: string;
  active: number;
  total: number;
  last_seen_at: string | null;
  first_collected_at: string | null;
};

type ScrapeRun = {
  run_id: string;
  platform: string;
  started_at: string;
  finished_at: string;
  status: "ok" | "failed" | "skipped";
  fetched: number;
  saved: number;
  new_count: number;
  closed_count: number;
  error: string | null;
};

type HistoryRow = { collected_at: string; platform: string; new_count: number };

const KST = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

/** 2026. 11. 05. 16:17 → 2026-11-05 16:17 (KST) */
function kst(iso: string | null): string {
  if (!iso) return "-";
  const parts = Object.fromEntries(KST.formatToParts(new Date(iso)).map((p) => [p.type, p.value]));
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}`;
}

function seconds(from: string, to: string): string {
  const s = Math.round((new Date(to).getTime() - new Date(from).getTime()) / 1000);
  return s >= 60 ? `${Math.floor(s / 60)}분 ${s % 60}초` : `${s}초`;
}

export default function AdminPage() {
  return (
    <div className="mx-auto w-full max-w-3xl flex-1 bg-card px-4 py-6 sm:px-6">
      <h1 className="text-xl font-bold tracking-tight text-foreground">수집 현황</h1>
      <p className="mt-1 text-xs text-muted-foreground">모든 시각은 한국 시간(KST)입니다.</p>
      <Suspense fallback={<p className="mt-8 text-sm text-muted-foreground">불러오는 중…</p>}>
        <AdminData />
      </Suspense>
    </div>
  );
}

async function AdminData() {
  await connection(); // 열 때마다 최신 값

  const [status, runs, history] = await Promise.all([
    supabase.from("admin_platform_status").select("*").order("platform"),
    supabase.from("scrape_runs").select("*").order("started_at", { ascending: false }).limit(300),
    supabase.from("admin_collection_history").select("*").order("collected_at", { ascending: false }).limit(1000),
  ]);

  const error = status.error ?? runs.error ?? history.error;
  if (error) {
    return <p className="mt-8 text-sm text-coral">데이터를 불러오지 못했습니다: {error.message}</p>;
  }

  return (
    <>
      <PlatformTable rows={(status.data ?? []) as PlatformStatus[]} />
      <RunList runs={(runs.data ?? []) as ScrapeRun[]} />
      <HistoryList rows={(history.data ?? []) as HistoryRow[]} />
    </>
  );
}

function Section({ title, note, children }: { title: string; note?: string; children: React.ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="text-[15px] font-semibold text-foreground">{title}</h2>
      {note && <p className="mt-0.5 text-xs text-muted-foreground">{note}</p>}
      <div className="mt-3 overflow-x-auto rounded-xl border border-border">{children}</div>
    </section>
  );
}

const TH = "whitespace-nowrap px-3 py-2 text-left text-xs font-medium text-muted-foreground";
const TD = "whitespace-nowrap px-3 py-2 tabular-nums";

function PlatformTable({ rows }: { rows: PlatformStatus[] }) {
  return (
    <Section title="플랫폼별 상태" note="마지막 확인 = 수집 때 사이트 목록에서 마지막으로 본 시각">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className={TH}>플랫폼</th>
            <th className={cn(TH, "text-right")}>모집 중</th>
            <th className={cn(TH, "text-right")}>전체</th>
            <th className={TH}>마지막 확인</th>
            <th className={TH}>처음 수집</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((r) => (
            <tr key={r.platform}>
              <td className={cn(TD, "font-medium")}>{r.platform}</td>
              <td className={cn(TD, "text-right")}>{r.active.toLocaleString()}</td>
              <td className={cn(TD, "text-right text-muted-foreground")}>{r.total.toLocaleString()}</td>
              <td className={TD}>{kst(r.last_seen_at)}</td>
              <td className={cn(TD, "text-muted-foreground")}>{kst(r.first_collected_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}

const STATUS_LABEL: Record<ScrapeRun["status"], { text: string; className: string }> = {
  ok: { text: "성공", className: "bg-mint/10 text-mint" },
  failed: { text: "실패", className: "bg-coral/10 text-coral" },
  skipped: { text: "건너뜀", className: "bg-muted text-muted-foreground" },
};

function RunList({ runs }: { runs: ScrapeRun[] }) {
  // 같은 회차(run_id)끼리 묶고, 회차는 시작 시각 최신순
  const groups = new Map<string, ScrapeRun[]>();
  for (const r of runs) groups.set(r.run_id, [...(groups.get(r.run_id) ?? []), r]);

  return (
    <Section title="수집 회차" note="회차마다 플랫폼별 결과 · 읽음 = 사이트 목록 건수, 저장 = 정제 후 DB에 쓴 건수, 신규 = 처음 들어온 캠페인, 종료 = 목록에서 사라져 내린 캠페인">
      {groups.size === 0 ? (
        <p className="px-3 py-4 text-sm text-muted-foreground">아직 기록이 없습니다. 다음 정기 수집부터 쌓입니다.</p>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className={TH}>시작</th>
              <th className={TH}>플랫폼</th>
              <th className={TH}>결과</th>
              <th className={cn(TH, "text-right")}>읽음</th>
              <th className={cn(TH, "text-right")}>저장</th>
              <th className={cn(TH, "text-right")}>신규</th>
              <th className={cn(TH, "text-right")}>종료</th>
              <th className={TH}>걸린 시간</th>
            </tr>
          </thead>
          {[...groups.values()].map((items) => {
            const sorted = [...items].sort((a, b) => a.started_at.localeCompare(b.started_at));
            return (
              <tbody key={sorted[0].run_id} className="divide-y divide-border border-t-2 border-border">
                {sorted.map((r, i) => (
                  <tr key={r.platform + r.started_at} className="align-top">
                    <td className={cn(TD, "font-medium")}>{i === 0 ? kst(r.started_at) : ""}</td>
                    <td className={TD}>{r.platform}</td>
                    <td className={TD}>
                      <span className={cn("rounded px-1.5 py-0.5 text-xs font-medium", STATUS_LABEL[r.status].className)}>
                        {STATUS_LABEL[r.status].text}
                      </span>
                      {r.error && (
                        <p className="mt-1 w-56 whitespace-normal break-words text-xs text-muted-foreground">{r.error}</p>
                      )}
                    </td>
                    <td className={cn(TD, "text-right")}>{r.fetched.toLocaleString()}</td>
                    <td className={cn(TD, "text-right")}>{r.saved.toLocaleString()}</td>
                    <td className={cn(TD, "text-right font-medium")}>{r.new_count.toLocaleString()}</td>
                    <td className={cn(TD, "text-right text-muted-foreground")}>{(r.closed_count ?? 0).toLocaleString()}</td>
                    <td className={cn(TD, "text-muted-foreground")}>{seconds(r.started_at, r.finished_at)}</td>
                  </tr>
                ))}
              </tbody>
            );
          })}
        </table>
      )}
    </Section>
  );
}

function HistoryList({ rows }: { rows: HistoryRow[] }) {
  // 한 회차에 들어온 캠페인은 created_at이 같다 → 시각별로 묶어 플랫폼별 신규 건수를 보여 준다
  const groups = new Map<string, HistoryRow[]>();
  for (const r of rows) groups.set(r.collected_at, [...(groups.get(r.collected_at) ?? []), r]);

  return (
    <Section
      title="새 캠페인이 들어온 시각"
      note="캠페인의 최초 수집 시각으로 복원한 기록 (수집 회차 기록 이전 포함, 신규 0건인 회차는 빠짐)"
    >
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className={TH}>수집 시각</th>
            <th className={cn(TH, "text-right")}>신규</th>
            <th className={TH}>플랫폼별</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {[...groups.entries()].map(([at, items]) => (
            <tr key={at}>
              <td className={cn(TD, "font-medium")}>{kst(at)}</td>
              <td className={cn(TD, "text-right")}>{items.reduce((n, r) => n + r.new_count, 0).toLocaleString()}</td>
              <td className={cn(TD, "whitespace-normal text-muted-foreground")}>
                {items
                  .sort((a, b) => b.new_count - a.new_count)
                  .map((r) => `${r.platform} ${r.new_count}`)
                  .join(" · ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}
