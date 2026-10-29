import { supabase } from "@/lib/supabase";

// 신규 체험단 사이트 추가 요청 — DB에 저장하고, 설정돼 있으면 운영자에게 메일로 알린다.
//
// 메일 발송 환경변수 (Vercel 프로젝트 설정에 등록):
//   RESEND_API_KEY        https://resend.com 에서 발급
//   PLATFORM_REQUEST_TO   요청을 받을 운영자 메일 주소
//   PLATFORM_REQUEST_FROM 보내는 주소 (기본: Resend 테스트 발신자 — 도메인 인증 전에는
//                         Resend 계정 메일로만 보낼 수 있다)
// 메일 설정이 없어도 요청은 DB(platform_requests)에 저장된다.

const LIMITS = { siteName: 100, siteUrl: 500, note: 1000, email: 200 };
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface RequestBody {
  siteName?: unknown;
  siteUrl?: unknown;
  note?: unknown;
  email?: unknown;
  /** 봇 방지용 숨은 칸 — 사람은 비워 둔다 */
  website?: unknown;
}

function text(value: unknown, max: number): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed.slice(0, max) : null;
}

function normalizeUrl(value: string | null): string | null {
  if (!value) return null;
  const withScheme = /^https?:\/\//i.test(value) ? value : `https://${value}`;
  try {
    const url = new URL(withScheme);
    return url.hostname.includes(".") ? url.toString() : null;
  } catch {
    return null;
  }
}

export async function POST(request: Request) {
  let body: RequestBody;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "요청 형식이 올바르지 않아요." }, { status: 400 });
  }

  // 봇이 숨은 칸까지 채운 경우: 성공한 척하고 아무것도 하지 않는다
  if (text(body.website, 200)) return Response.json({ ok: true });

  const siteName = text(body.siteName, LIMITS.siteName);
  const rawUrl = text(body.siteUrl, LIMITS.siteUrl);
  const siteUrl = normalizeUrl(rawUrl);
  const note = text(body.note, LIMITS.note);
  const email = text(body.email, LIMITS.email);

  if (!siteName) {
    return Response.json({ error: "사이트 이름을 입력해 주세요." }, { status: 400 });
  }
  if (rawUrl && !siteUrl) {
    return Response.json({ error: "사이트 주소를 확인해 주세요. 예) www.example.com" }, { status: 400 });
  }
  if (email && !EMAIL_RE.test(email)) {
    return Response.json({ error: "답장 받을 메일 주소를 확인해 주세요." }, { status: 400 });
  }

  const { error } = await supabase
    .from("platform_requests")
    .insert({ site_name: siteName, site_url: siteUrl, note, contact_email: email });
  if (error) {
    console.error("platform_requests insert failed", error);
    return Response.json({ error: "요청을 저장하지 못했어요. 잠시 후 다시 시도해 주세요." }, { status: 500 });
  }

  const emailed = await notifyAdmin({ siteName, siteUrl, note, email });
  return Response.json({ ok: true, emailed });
}

async function notifyAdmin(req: {
  siteName: string;
  siteUrl: string | null;
  note: string | null;
  email: string | null;
}): Promise<boolean> {
  const apiKey = process.env.RESEND_API_KEY;
  const to = process.env.PLATFORM_REQUEST_TO;
  if (!apiKey || !to) return false;

  const lines = [
    `사이트: ${req.siteName}`,
    `주소: ${req.siteUrl ?? "(없음)"}`,
    `요청자 메일: ${req.email ?? "(없음)"}`,
    "",
    req.note ?? "(메모 없음)",
    "",
    "— BLEACH 신규 플랫폼 요청 (Supabase platform_requests 테이블에도 저장됨)",
  ];

  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        from: process.env.PLATFORM_REQUEST_FROM ?? "BLEACH <onboarding@resend.dev>",
        to: [to],
        subject: `[BLEACH] 신규 체험단 사이트 요청: ${req.siteName}`,
        text: lines.join("\n"),
        ...(req.email ? { reply_to: req.email } : {}),
      }),
    });
    if (!res.ok) console.error("resend failed", res.status, await res.text());
    return res.ok;
  } catch (e) {
    // 메일이 실패해도 요청은 이미 저장됐으니 사용자에게는 성공으로 응답한다
    console.error("resend error", e);
    return false;
  }
}
