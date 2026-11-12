// Google AdSense 설정.
//
//   NEXT_PUBLIC_ADSENSE_CLIENT      게시자 ID (기본값: 이 사이트의 ca-pub-2018630083097143). 비워 둘 수는 없고 다른 값으로 바꿀 때만 설정.
//   NEXT_PUBLIC_ADSENSE_SLOT        광고 단위 ID (기본값: 피드 내 광고 1293649683). 다른 단위로 바꿀 때만 설정.
//   NEXT_PUBLIC_ADSENSE_LAYOUT_KEY  피드형 광고의 layout key (기본값: -fi+6j-17-cv+rc).
//
// - 게시자 ID만 있으면: <head>에 AdSense 코드가 나온다 (사이트 연결·소유 확인용). 광고 칸은 없다.
//   (/ads.txt는 넣지 않았다. 나중에 AdSense가 요구하면 `google.com, pub-<ID>, DIRECT, f08c47fec0942fa0` 한 줄짜리 route를 다시 만든다.)
// - 광고 단위 ID까지 있으면: 목록 사이에 광고 칸이 들어간다.
// 켜기 전에 확인할 것은 README의 "광고" 절 (호스팅 약관, 본인 도메인, 개인정보처리방침, 승인).

export const ADSENSE_CLIENT = process.env.NEXT_PUBLIC_ADSENSE_CLIENT || "ca-pub-2018630083097143";
// 피드 내 광고 단위 (AdSense에서 만든 값). 환경변수로 바꿀 수 있다.
export const ADSENSE_SLOT = process.env.NEXT_PUBLIC_ADSENSE_SLOT || "1293649683";
export const ADSENSE_LAYOUT_KEY = process.env.NEXT_PUBLIC_ADSENSE_LAYOUT_KEY || "-fi+6j-17-cv+rc";

/** 게시자 ID가 올바른 모양일 때만 AdSense 코드를 내보낸다 — 오타가 있으면 조용히 꺼진다. */
export const scriptEnabled = /^ca-pub-\d{10,}$/.test(ADSENSE_CLIENT);

/** 광고 단위 ID까지 올바를 때만 목록 사이 광고 칸을 넣는다. */
export const adsEnabled = scriptEnabled && /^\d{6,}$/.test(ADSENSE_SLOT);

/** 캠페인 몇 개마다 광고 한 칸을 넣을지 */
export const AD_EVERY = 8;
/** 한 화면(무한 스크롤을 계속 내려도)에서 넣을 광고 칸의 최대 개수 */
export const AD_MAX = 6;

// 쿠팡 파트너스 다이나믹 배너 (파트너스에서 만든 값). 환경변수로 바꾸거나 NEXT_PUBLIC_COUPANG_ID=off 로 끈다.
export const COUPANG = {
  id: Number(process.env.NEXT_PUBLIC_COUPANG_ID || 1049608),
  trackingCode: process.env.NEXT_PUBLIC_COUPANG_TRACKING || "AF6737478",
  template: "carousel",
  width: 320,
  height: 100,
};
export const coupangEnabled = process.env.NEXT_PUBLIC_COUPANG_ID !== "off" && Number.isInteger(COUPANG.id) && COUPANG.id > 0;

export type AdKind = "coupang" | "adsense";

/**
 * index번째(0부터) 캠페인 바로 뒤에 넣을 광고 (없으면 null).
 * 8개마다 한 칸, 최대 6칸 — 1·3·5번째 칸은 쿠팡 파트너스, 2·4·6번째는 애드센스.
 * 한쪽만 켜져 있으면 그쪽이 모든 칸을 쓴다. 애드센스는 이 사이트가 승인되기 전에는 채워지지 않아 칸째 숨는다.
 */
export function adAfter(index: number): AdKind | null {
  const count = index + 1;
  if (count % AD_EVERY !== 0 || count / AD_EVERY > AD_MAX) return null;
  const nth = count / AD_EVERY; // 1부터
  if (coupangEnabled && adsEnabled) return nth % 2 === 1 ? "coupang" : "adsense";
  if (coupangEnabled) return "coupang";
  if (adsEnabled) return "adsense";
  return null;
}
