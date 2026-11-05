import { HomeClient } from "@/components/home-client";
import { encodeFilters } from "@/lib/campaigns";
import { EMPTY_FILTER_STATE, toQuery } from "@/lib/filter-state";
import { cachedHomeData } from "@/lib/server-data";

// 첫 화면(기본 조건: 마감임박순, 조건 없음)의 체험단 30개를 서버에서 미리 HTML로 그려 보낸다.
// 검색엔진·광고 심사 크롤러가 자바스크립트를 실행하지 않아도 내용이 보이게 하기 위해서다.
// 캐시된 조회라 몇 분 동안은 같은 결과를 다시 쓴다. DB에 못 닿으면 null — 그때는 브라우저가 불러온다.
export default async function Page() {
  const initial = await cachedHomeData(encodeFilters(toQuery("", EMPTY_FILTER_STATE, [])));
  return <HomeClient initial={initial} />;
}
