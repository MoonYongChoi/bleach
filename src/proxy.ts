import { NextResponse, type NextRequest } from "next/server";

/**
 * /admin 은 Basic 인증으로 막는다. Vercel 환경변수 ADMIN_PASSWORD(필수)와 ADMIN_USER(선택, 기본 "admin").
 * 비밀번호를 설정하지 않으면 페이지가 없는 것처럼 404를 돌려준다.
 */
export function proxy(request: NextRequest) {
  const password = process.env.ADMIN_PASSWORD;
  if (!password) return new NextResponse("Not Found", { status: 404 });
  const user = process.env.ADMIN_USER || "admin";

  const header = request.headers.get("authorization") ?? "";
  if (header.startsWith("Basic ")) {
    let decoded = "";
    try {
      decoded = atob(header.slice(6));
    } catch {
      decoded = "";
    }
    if (safeEqual(decoded, `${user}:${password}`)) return NextResponse.next();
  }
  return new NextResponse("인증이 필요합니다", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="bleach admin", charset="UTF-8"' },
  });
}

/** 길이가 같을 때 글자마다 비교 시간을 같게 */
function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export const config = {
  matcher: ["/admin", "/admin/:path*"],
};
