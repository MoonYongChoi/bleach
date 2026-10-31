import { cacheLife } from "next/cache";
import { fetchCampaignPage, parseFilters } from "@/lib/campaigns";

// 체험단 목록의 한 페이지. 같은 조건이면 같은 응답이 나오므로 서버 캐시 + CDN 캐시로 DB 조회를 줄인다.
// 검색어가 있는 요청은 입력이 무한히 다양해 캐시 키가 끝없이 늘 수 있어서 서버 캐시는 쓰지 않고 짧게만 CDN에 둔다.
async function cachedPage(query: string, page: number) {
  "use cache";
  cacheLife({ stale: 60, revalidate: 300, expire: 3600 });
  return fetchCampaignPage(parseFilters(query) ?? {}, page);
}

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const raw = params.get("q") ?? "{}";
  const filters = parseFilters(raw);
  const page = Number(params.get("page") ?? "0");
  if (!filters || !Number.isInteger(page) || page < 0 || page > 200) {
    return Response.json({ error: "bad_request" }, { status: 400, headers: { "Cache-Control": "no-store" } });
  }
  try {
    const searching = Boolean(filters.search);
    const rows = searching ? await fetchCampaignPage(filters, page) : await cachedPage(raw, page);
    return Response.json(
      { rows },
      {
        headers: {
          "Cache-Control": searching
            ? "public, s-maxage=60, stale-while-revalidate=300"
            : "public, s-maxage=300, stale-while-revalidate=3600",
        },
      }
    );
  } catch (e) {
    console.error("campaigns failed", e);
    return Response.json({ error: "unavailable" }, { status: 502, headers: { "Cache-Control": "no-store" } });
  }
}
