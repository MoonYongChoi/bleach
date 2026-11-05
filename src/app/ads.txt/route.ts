import { ADSENSE_CLIENT, scriptEnabled } from "@/lib/ads";

// AdSense가 사이트 소유를 확인하는 /ads.txt. 게시자 ID가 설정돼 있을 때만 내용을 돌려주고, 아니면 404.
// f08c47fec0942fa0은 구글의 고정 인증 기관 ID다.
export function GET() {
  if (!scriptEnabled) return new Response("Not found", { status: 404 });
  const publisher = ADSENSE_CLIENT.replace(/^ca-/, "");
  return new Response(`google.com, ${publisher}, DIRECT, f08c47fec0942fa0\n`, {
    headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "public, max-age=3600" },
  });
}
