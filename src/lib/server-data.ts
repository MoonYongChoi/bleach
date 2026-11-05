import { cacheLife } from "next/cache";
import { countCampaigns, fetchCampaignPage, fetchFilterOptions, parseFilters } from "@/lib/campaigns";

// 서버에서만 쓰는 캐시된 조회. 첫 화면 미리 그리기(app/page.tsx)와 /api 경로가 같은 캐시를 함께 쓴다.
// 데이터는 하루 몇 번 수집할 때만 바뀌므로 몇 분 동안은 같은 결과를 다시 쓴다. query는 encodeFilters()의 결과.

export async function cachedFilterOptions() {
  "use cache";
  cacheLife({ stale: 300, revalidate: 900, expire: 86400 });
  return fetchFilterOptions();
}

export async function cachedCampaignPage(query: string, page: number) {
  "use cache";
  cacheLife({ stale: 60, revalidate: 300, expire: 3600 });
  return fetchCampaignPage(parseFilters(query) ?? {}, page);
}

export async function cachedCampaignCount(query: string) {
  "use cache";
  cacheLife({ stale: 60, revalidate: 300, expire: 3600 });
  return countCampaigns(parseFilters(query) ?? {});
}

/**
 * 첫 화면(app/page.tsx)용: 목록 첫 묶음·개수·필터 선택지를 한 번에. DB에 못 닿으면 null을 돌려준다.
 * 캐시 함수 안에서 난 오류는 바깥에서 잡아도 미리 그리기 실패로 빌드가 멈추므로, 여기서(안쪽에서) 잡는다.
 * null도 몇 분 동안 캐시되지만 그동안은 브라우저가 /api로 직접 불러오므로 화면은 정상이다.
 */
export async function cachedHomeData(query: string) {
  "use cache";
  cacheLife({ stale: 60, revalidate: 300, expire: 3600 });
  try {
    const filters = parseFilters(query) ?? {};
    const [rows, total, options] = await Promise.all([
      fetchCampaignPage(filters, 0),
      countCampaigns(filters),
      fetchFilterOptions(),
    ]);
    return { rows, total, options };
  } catch (e) {
    console.error("home data unavailable — page will load client-side", e);
    return null;
  }
}
