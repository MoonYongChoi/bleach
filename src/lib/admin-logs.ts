// /admin/logs 원본 기록 조회 (서버 전용). 원본 행은 공개 키로 읽을 수 없게 막아 두었으므로
// Vercel 환경변수 SUPABASE_SERVICE_ROLE_KEY(서비스 키, NEXT_PUBLIC_ 아님)로 읽는다. 브라우저 코드에서 import 하지 말 것.
import { createClient } from "@supabase/supabase-js";

export const LOG_EVENTS = ["page_view", "search", "filter", "click"] as const;
export type LogEvent = (typeof LOG_EVENTS)[number];

export interface LogRow {
  id: number;
  ts: string;
  event: LogEvent;
  session: string;
  path: string | null;
  referrer: string | null;
  device: string | null;
  country: string | null;
  data: Record<string, unknown>;
}

export interface LogQuery {
  event?: LogEvent;
  from?: string; // YYYY-MM-DD (KST, 그날 0시부터)
  to?: string; // YYYY-MM-DD (KST, 그날 끝까지)
  session?: string; // 앞부분 일치
  q?: string; // 경로·유입·검색어·필터 요약·체험단 이름·플랫폼에서 찾기
  device?: string;
  country?: string;
  limit: number;
  page: number; // 0부터
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v)?.trim() || undefined;
// PostgREST or() 문법을 깨는 문자는 뺀다
const clean = (v: string | undefined, max = 60) => v?.replace(/[,()*\\%]/g, " ").trim().slice(0, max) || undefined;

export function parseLogQuery(sp: Record<string, string | string[] | undefined>, maxLimit = 1000): LogQuery {
  const event = one(sp.event) as LogEvent | undefined;
  const from = one(sp.from);
  const to = one(sp.to);
  const limit = Math.min(Math.max(Number(one(sp.limit)) || 100, 10), maxLimit);
  return {
    event: event && (LOG_EVENTS as readonly string[]).includes(event) ? event : undefined,
    from: from && DATE_RE.test(from) ? from : undefined,
    to: to && DATE_RE.test(to) ? to : undefined,
    session: clean(one(sp.session), 64),
    q: clean(one(sp.q)),
    device: one(sp.device) === "mobile" || one(sp.device) === "desktop" ? one(sp.device) : undefined,
    country: clean(one(sp.country), 4)?.toUpperCase(),
    limit,
    page: Math.max(Number(one(sp.page)) || 0, 0),
  };
}

export function hasServiceKey(): boolean {
  return Boolean(process.env.SUPABASE_SERVICE_ROLE_KEY);
}

export async function queryLogs(query: LogQuery): Promise<{ rows: LogRow[]; total: number | null; error?: string }> {
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!key) return { rows: [], total: null, error: "SUPABASE_SERVICE_ROLE_KEY가 설정되지 않았습니다" };
  const admin = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  let q = admin.from("access_logs").select("*", { count: "exact" });
  if (query.event) q = q.eq("event", query.event);
  if (query.from) q = q.gte("ts", `${query.from}T00:00:00+09:00`);
  if (query.to) q = q.lte("ts", `${query.to}T23:59:59.999+09:00`);
  if (query.session) q = q.ilike("session", `${query.session}%`);
  if (query.device) q = q.eq("device", query.device);
  if (query.country) q = q.eq("country", query.country);
  if (query.q) {
    const like = `*${query.q}*`;
    q = q.or(
      ["path", "referrer", "data->>q", "data->>summary", "data->>title", "data->>platform"]
        .map((col) => `${col}.ilike.${like}`)
        .join(",")
    );
  }
  const from = query.page * query.limit;
  const { data, count, error } = await q.order("ts", { ascending: false }).order("id", { ascending: false }).range(from, from + query.limit - 1);
  if (error) return { rows: [], total: null, error: error.message };
  return { rows: (data ?? []) as LogRow[], total: count };
}

/** 쿼리를 다시 URL 검색어로 (페이지 이동·CSV 링크용) */
export function logQueryString(query: LogQuery, patch: Partial<LogQuery> = {}): string {
  const merged = { ...query, ...patch };
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(merged)) {
    if (v === undefined || v === "" || (k === "page" && v === 0) || (k === "limit" && v === 100)) continue;
    params.set(k, String(v));
  }
  const s = params.toString();
  return s ? `?${s}` : "";
}
