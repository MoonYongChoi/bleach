import { connection } from "next/server";

// 임시: Vercel 서울 리전(icn1)에서 서울오빠 목록 페이지에 접속되는지 시험한다.
// 주소가 고정이라 다른 곳으로 요청을 보낼 수 없고, 결과는 1분간 CDN에 캐시해 반복 호출이 사이트로 가지 않게 한다.
const TARGET = "https://www.seoulouba.co.kr/campaign/?cat=377";

export async function GET() {
  await connection();
  const started = Date.now();
  const region = process.env.VERCEL_REGION ?? "local";
  try {
    const res = await fetch(TARGET, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
      },
      signal: AbortSignal.timeout(20_000),
      cache: "no-store",
    });
    const html = await res.text();
    return Response.json(
      {
        region,
        ok: res.ok,
        status: res.status,
        ms: Date.now() - started,
        bytes: html.length,
        title: html.match(/<title[^>]*>([^<]*)<\/title>/i)?.[1]?.trim() ?? null,
        campaignLinks: (html.match(/campaign\/\?c=\d+/g) ?? []).length,
      },
      { headers: { "Cache-Control": "public, s-maxage=60" } }
    );
  } catch (e) {
    const err = e as Error & { cause?: { code?: string } };
    return Response.json(
      { region, ok: false, ms: Date.now() - started, error: `${err.name}: ${err.message}`, cause: err.cause?.code ?? null },
      { status: 502, headers: { "Cache-Control": "public, s-maxage=60" } }
    );
  }
}
