import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { hasServiceKey, LOG_EVENTS, logQueryString, parseLogQuery, queryLogs, type LogQuery, type LogRow } from "@/lib/admin-logs";
import { cn } from "cn";

export const metadata: Metadata = {
  title: "원본 기록 — bleach admin",
  robots: { index: false, follow: false },
};

const EVENT_LABELS: Record<string, string> = { page_view: "방문", search: "검색", filter: "필터", click: "클릭" };
const SQL_EDITOR = "https://supabase.com/dashboard/project/ylykhtfnxbqopijpqknn/sql/new";
const SQL_EXAMPLES = `-- 최근 100건
select ts at time zone 'Asia/Seoul' as kst, event, session, path, referrer, device, country, data
from access_logs order by ts desc limit 100;

-- 시간대별 방문 (최근 7일, KST)
select date_trunc('hour', ts at time zone 'Asia/Seoul') as hour, count(*) filter (where event = 'page_view') as views,
       count(distinct session) as tabs
from access_logs where ts > now() - interval '7 days' group by 1 order by 1 desc;

-- 한 탭의 행동 순서
select ts at time zone 'Asia/Seoul', event, data from access_logs where session like 'abc123%' order by ts;

-- 검색 후 클릭까지 이어진 비율 (최근 7일)
select count(distinct session) filter (where event = 'search') as searched,
       count(distinct session) filter (where event = 'click' and session in
         (select session from access_logs where event = 'search')) as searched_then_clicked
from access_logs where ts > now() - interval '7 days';`;

const KST = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});
function kst(iso: string): string {
  const p = Object.fromEntries(KST.formatToParts(new Date(iso)).map((x) => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}:${p.second}`;
}

export default function RawLogsPage({ searchParams }: PageProps<"/admin/logs">) {
  return (
    <div className="mx-auto w-full max-w-6xl flex-1 bg-card px-4 py-6 sm:px-6">
      <div className="flex items-baseline justify-between gap-3">
        <h1 className="text-xl font-bold tracking-tight text-foreground">원본 기록</h1>
        <span className="flex gap-3 text-sm">
          <Link href="/admin/logs/summary" className="text-primary hover:underline">
            요약 →
          </Link>
          <Link href="/admin" className="text-primary hover:underline">
            수집 현황 →
          </Link>
        </span>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        시각은 한국 시간. 기록은 90일 보관. 탭 값을 누르면 그 탭의 기록만 봅니다.
      </p>
      <Suspense fallback={<p className="mt-8 text-sm text-muted-foreground">불러오는 중…</p>}>
        <RawLogs searchParams={searchParams} />
      </Suspense>
      <details className="mt-10 rounded-xl border border-border p-4">
        <summary className="cursor-pointer text-sm font-semibold text-foreground">SQL로 직접 조회하기</summary>
        <p className="mt-2 text-sm text-muted-foreground">
          자유로운 쿼리는{" "}
          <a href={SQL_EDITOR} target="_blank" rel="noopener noreferrer" className="text-primary underline">
            Supabase SQL 편집기
          </a>
          에서 <code className="rounded bg-muted px-1">access_logs</code> 테이블을 조회하세요. 열: id, ts, event(page_view·search·filter·click),
          session, path, referrer, device, country, data(jsonb: q / summary / id·platform·title).
        </p>
        <pre className="mt-3 overflow-x-auto rounded-lg bg-muted p-3 text-xs leading-relaxed">{SQL_EXAMPLES}</pre>
      </details>
    </div>
  );
}

async function RawLogs({ searchParams }: { searchParams: PageProps<"/admin/logs">["searchParams"] }) {
  const query = parseLogQuery(await searchParams);
  if (!hasServiceKey()) {
    return (
      <div className="mt-6 rounded-xl border border-border bg-muted/40 p-4 text-sm">
        원본 기록은 서버 전용 키로 읽습니다. Vercel → Settings → Environment Variables에{" "}
        <code className="rounded bg-muted px-1">SUPABASE_SERVICE_ROLE_KEY</code>를 넣고(값: Supabase → Project Settings → API
        Keys의 service_role / secret 키) 다시 배포하세요. 요약은{" "}
        <Link href="/admin/logs/summary" className="text-primary underline">
          여기
        </Link>
        에서 볼 수 있습니다.
      </div>
    );
  }
  const { rows, total, error } = await queryLogs(query);
  const pages = total ? Math.ceil(total / query.limit) : 0;

  return (
    <>
      <Filters query={query} />
      {error ? (
        <p className="mt-6 text-sm text-coral">불러오지 못했습니다: {error}</p>
      ) : (
        <>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm">
            <span className="text-muted-foreground">
              {total?.toLocaleString() ?? 0}건 중 {rows.length ? query.page * query.limit + 1 : 0}–
              {query.page * query.limit + rows.length}
            </span>
            <span className="flex items-center gap-3">
              <a href={`/admin/logs/export${logQueryString(query, { page: 0 })}`} className="text-primary hover:underline">
                CSV로 받기 (최대 1만 건)
              </a>
              <Pager query={query} pages={pages} />
            </span>
          </div>
          <LogTable rows={rows} query={query} />
          <div className="mt-3 flex justify-end text-sm">
            <Pager query={query} pages={pages} />
          </div>
        </>
      )}
    </>
  );
}

function Filters({ query }: { query: LogQuery }) {
  const field = "h-9 rounded-lg border border-border bg-background px-2 text-sm";
  return (
    <form method="get" className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
      <select name="event" defaultValue={query.event ?? ""} className={field} aria-label="종류">
        <option value="">모든 종류</option>
        {LOG_EVENTS.map((e) => (
          <option key={e} value={e}>
            {EVENT_LABELS[e]}
          </option>
        ))}
      </select>
      <input type="date" name="from" defaultValue={query.from} className={field} aria-label="시작일" />
      <input type="date" name="to" defaultValue={query.to} className={field} aria-label="종료일" />
      <input name="q" defaultValue={query.q} placeholder="내용 검색" className={cn(field, "col-span-2")} aria-label="내용 검색" />
      <input name="session" defaultValue={query.session} placeholder="탭(앞부분)" className={field} aria-label="탭" />
      <select name="device" defaultValue={query.device ?? ""} className={field} aria-label="기기">
        <option value="">모든 기기</option>
        <option value="mobile">모바일</option>
        <option value="desktop">PC</option>
      </select>
      <input name="country" defaultValue={query.country} placeholder="국가 (KR)" className={field} aria-label="국가" />
      <select name="limit" defaultValue={String(query.limit)} className={field} aria-label="한 쪽에 보일 수">
        {[50, 100, 300, 1000].map((n) => (
          <option key={n} value={n}>
            {n}건씩
          </option>
        ))}
      </select>
      <div className="col-span-2 flex gap-2 sm:col-span-3 lg:col-span-7">
        <button type="submit" className="h-9 rounded-lg bg-primary px-4 text-sm font-semibold text-primary-foreground">
          조회
        </button>
        <Link href="/admin/logs" className="flex h-9 items-center rounded-lg border border-border px-4 text-sm">
          초기화
        </Link>
      </div>
    </form>
  );
}

function Pager({ query, pages }: { query: LogQuery; pages: number }) {
  if (pages <= 1) return null;
  const link = (page: number, label: string, disabled: boolean) =>
    disabled ? (
      <span className="text-muted-foreground/50">{label}</span>
    ) : (
      <Link href={`/admin/logs${logQueryString(query, { page })}`} className="text-primary hover:underline">
        {label}
      </Link>
    );
  return (
    <span className="flex items-center gap-2 tabular-nums">
      {link(query.page - 1, "← 이전", query.page === 0)}
      <span className="text-muted-foreground">
        {query.page + 1} / {pages}
      </span>
      {link(query.page + 1, "다음 →", query.page + 1 >= pages)}
    </span>
  );
}

const TH = "whitespace-nowrap px-2 py-2 text-left text-xs font-medium text-muted-foreground";
const TD = "px-2 py-1.5 align-top";

function LogTable({ rows, query }: { rows: LogRow[]; query: LogQuery }) {
  if (rows.length === 0) return <p className="mt-6 text-sm text-muted-foreground">조건에 맞는 기록이 없습니다.</p>;
  return (
    <div className="mt-2 overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-xs">
        <thead className="bg-muted/50">
          <tr>
            <th className={TH}>시각</th>
            <th className={TH}>종류</th>
            <th className={TH}>탭</th>
            <th className={TH}>경로</th>
            <th className={TH}>유입</th>
            <th className={TH}>기기</th>
            <th className={TH}>국가</th>
            <th className={TH}>데이터</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((r) => (
            <tr key={r.id}>
              <td className={cn(TD, "whitespace-nowrap tabular-nums text-muted-foreground")}>{kst(r.ts)}</td>
              <td className={cn(TD, "whitespace-nowrap")}>{EVENT_LABELS[r.event] ?? r.event}</td>
              <td className={cn(TD, "font-mono")}>
                <Link href={`/admin/logs${logQueryString({ ...query, page: 0 }, { session: r.session })}`} className="text-primary hover:underline">
                  {r.session}
                </Link>
              </td>
              <td className={cn(TD, "whitespace-nowrap")}>{r.path}</td>
              <td className={cn(TD, "whitespace-nowrap")}>{r.referrer || "–"}</td>
              <td className={TD}>{r.device}</td>
              <td className={TD}>{r.country ?? "–"}</td>
              <td className={cn(TD, "min-w-64 break-all font-mono")}>
                {Object.keys(r.data ?? {}).length ? JSON.stringify(r.data) : "–"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
