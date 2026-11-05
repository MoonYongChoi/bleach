// Google AdSense 설정.
//
//   NEXT_PUBLIC_ADSENSE_CLIENT      게시자 ID (기본값: 이 사이트의 ca-pub-2018630083097143). 비워 둘 수는 없고 다른 값으로 바꿀 때만 설정.
//   NEXT_PUBLIC_ADSENSE_SLOT        광고 단위 ID (숫자). AdSense에서 "피드 내 광고" 단위를 만들어 넣으면 목록 사이 광고 칸이 켜진다.
//   NEXT_PUBLIC_ADSENSE_LAYOUT_KEY  (선택) 피드형 광고의 layout key. 없으면 반응형 자동 크기.
//
// - 게시자 ID만 있으면: <head>에 AdSense 코드가 나온다 (사이트 연결·소유 확인용). 광고 칸은 없다.
//   (/ads.txt는 넣지 않았다. 나중에 AdSense가 요구하면 `google.com, pub-<ID>, DIRECT, f08c47fec0942fa0` 한 줄짜리 route를 다시 만든다.)
// - 광고 단위 ID까지 있으면: 목록 사이에 광고 칸이 들어간다.
// 켜기 전에 확인할 것은 README의 "광고" 절 (호스팅 약관, 본인 도메인, 개인정보처리방침, 승인).

export const ADSENSE_CLIENT = process.env.NEXT_PUBLIC_ADSENSE_CLIENT || "ca-pub-2018630083097143";
export const ADSENSE_SLOT = process.env.NEXT_PUBLIC_ADSENSE_SLOT ?? "";
export const ADSENSE_LAYOUT_KEY = process.env.NEXT_PUBLIC_ADSENSE_LAYOUT_KEY ?? "";

/** 게시자 ID가 올바른 모양일 때만 AdSense 코드를 내보낸다 — 오타가 있으면 조용히 꺼진다. */
export const scriptEnabled = /^ca-pub-\d{10,}$/.test(ADSENSE_CLIENT);

/** 광고 단위 ID까지 올바를 때만 목록 사이 광고 칸을 넣는다. */
export const adsEnabled = scriptEnabled && /^\d{6,}$/.test(ADSENSE_SLOT);

/** 캠페인 몇 개마다 광고 한 칸을 넣을지 */
export const AD_EVERY = 8;
/** 한 화면(무한 스크롤을 계속 내려도)에서 넣을 광고 칸의 최대 개수 */
export const AD_MAX = 6;

/** index번째(0부터) 캠페인 바로 뒤에 광고를 넣을지 */
export function adAfter(index: number): boolean {
  const count = index + 1;
  return adsEnabled && count % AD_EVERY === 0 && count / AD_EVERY <= AD_MAX;
}
