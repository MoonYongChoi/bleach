import { cacheLife } from "next/cache";
import { countCampaigns, parseFilters } from "@/lib/campaigns";

// 조건에 맞는 캠페인 수 ("총 N개", 필터 시트의 "N개 결과 보기"). 목록 API와 같은 캐시 전략.
async function cachedCount(query: string) {
  "use cache";
  cacheLife({ stale: 60, revalidate: 300, expire: 3600 });
  return countCampaigns(parseFilters(query) ?? {});
}

export async function GET(request: Request) {
  const raw = new URL(request.url).searchParams.get("q") ?? "{}";
  const filters = parseFilters(raw);
  if (!filters) {
    return Response.json({ error: "bad_request" }, { status: 400, headers: { "Cache-Control": "no-store" } });
  }
  try {
    const searching = Boolean(filters.search);
    const total = searching ? await countCampaigns(filters) : await cachedCount(raw);
    return Response.json(
      { total },
      {
        headers: {
          "Cache-Control": searching
            ? "public, s-maxage=60, stale-while-revalidate=300"
            : "public, s-maxage=300, stale-while-revalidate=3600",
        },
      }
    );
  } catch (e) {
    console.error("campaign count failed", e);
    return Response.json({ error: "unavailable" }, { status: 502, headers: { "Cache-Control": "no-store" } });
  }
}
