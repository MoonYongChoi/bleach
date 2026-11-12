import { hasServiceKey, parseLogQuery, queryLogs } from "@/lib/admin-logs";

// /admin/logs 의 현재 조건 그대로 CSV로 (최대 1만 건). /admin 경로라 proxy.ts의 비밀번호가 걸린다.
const MAX_ROWS = 10_000;
const PAGE = 1000; // Supabase API 한 번 응답 상한

const cell = (v: unknown) => {
  const s = v === null || v === undefined ? "" : typeof v === "string" ? v : JSON.stringify(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

export async function GET(request: Request) {
  if (!hasServiceKey()) return new Response("SUPABASE_SERVICE_ROLE_KEY가 설정되지 않았습니다", { status: 503 });
  const sp = Object.fromEntries(new URL(request.url).searchParams);
  const base = parseLogQuery(sp, PAGE);
  const lines = ["id,ts,event,session,path,referrer,device,country,data"];
  for (let page = 0; page * PAGE < MAX_ROWS; page++) {
    const { rows, error } = await queryLogs({ ...base, limit: PAGE, page });
    if (error) return new Response(error, { status: 500 });
    for (const r of rows) {
      lines.push([r.id, r.ts, r.event, r.session, r.path, r.referrer, r.device, r.country, r.data].map(cell).join(","));
    }
    if (rows.length < PAGE) break;
  }
  const stamp = new Date().toISOString().slice(0, 10);
  // 엑셀에서 한글이 깨지지 않게 BOM을 붙인다
  return new Response("﻿" + lines.join("\n"), {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": `attachment; filename="bleach-logs-${stamp}.csv"`,
      "cache-control": "no-store",
    },
  });
}
