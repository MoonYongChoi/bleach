import { cacheLife } from "next/cache";
import { connection } from "next/server";
import { fetchFilterOptions } from "@/lib/campaigns";

// 지역·카테고리 같은 필터 선택지. 데이터가 하루 몇 번만 바뀌므로 서버 캐시와 CDN 캐시를 길게 둔다.
// (예전에는 방문마다 브라우저가 활성 캠페인 전체를 받아 와서 집계했다 — 약 205 kB)
async function getOptions() {
  "use cache";
  cacheLife({ stale: 300, revalidate: 900, expire: 86400 });
  return fetchFilterOptions();
}

export async function GET() {
  await connection(); // 빌드 때 DB를 부르지 않고 요청 시점에 실행
  try {
    const options = await getOptions();
    return Response.json(options, {
      headers: { "Cache-Control": "public, s-maxage=900, stale-while-revalidate=86400" },
    });
  } catch (e) {
    console.error("filter-options failed", e);
    return Response.json({ error: "unavailable" }, { status: 502, headers: { "Cache-Control": "no-store" } });
  }
}
