import { supabase } from "@/lib/supabase";

// 브라우저가 보낸 이용 기록 한 건을 Supabase log_event()로 넘긴다. 검사·중복 거르기는 DB 함수가 한 번 더 한다.
const EVENTS = new Set(["page_view", "search", "filter", "click"]);
const BOT_RE = /bot|crawl|spider|slurp|preview|facebookexternalhit|headless/i;

export async function POST(request: Request) {
  const ua = request.headers.get("user-agent") ?? "";
  if (BOT_RE.test(ua)) return new Response(null, { status: 204 });

  const text = await request.text();
  if (text.length > 2000) return new Response(null, { status: 413 });
  let body: { event?: unknown; session?: unknown; path?: unknown; referrer?: unknown; data?: unknown };
  try {
    body = JSON.parse(text);
  } catch {
    return new Response(null, { status: 400 });
  }
  if (typeof body.event !== "string" || !EVENTS.has(body.event) || typeof body.session !== "string") {
    return new Response(null, { status: 400 });
  }
  const str = (v: unknown, max: number) => (typeof v === "string" ? v.slice(0, max) : null);
  const data = body.data && typeof body.data === "object" && !Array.isArray(body.data) ? body.data : {};

  const { error } = await supabase.rpc("log_event", {
    p_event: body.event,
    p_session: str(body.session, 64),
    p_path: str(body.path, 200),
    p_referrer: str(body.referrer, 100),
    p_device: /mobile|android|iphone|ipad/i.test(ua) ? "mobile" : "desktop",
    // Vercel이 붙여 주는 접속 국가 (로컬에서는 없음)
    p_country: request.headers.get("x-vercel-ip-country"),
    p_data: data,
  });
  if (error) console.error("log_event failed", error.message);
  return new Response(null, { status: 204 });
}
