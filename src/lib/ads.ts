// 목록 사이 광고: 쿠팡 파트너스 다이나믹 배너.
//
//   NEXT_PUBLIC_COUPANG_ID        배너 ID (기본값 1049608). "off"면 광고를 끈다.
//   NEXT_PUBLIC_COUPANG_TRACKING  트래킹 코드 (기본값 AF6737478).
//
// (구글 애드센스는 2026-11-12에 뺐다 — 다시 붙이려면 git 기록의 ad-slot.tsx·adsense-script.tsx 참고)

export const COUPANG = {
  id: Number(process.env.NEXT_PUBLIC_COUPANG_ID || 1049608),
  trackingCode: process.env.NEXT_PUBLIC_COUPANG_TRACKING || "AF6737478",
  template: "carousel",
  width: 320,
  height: 100,
};
export const coupangEnabled =
  process.env.NEXT_PUBLIC_COUPANG_ID !== "off" && Number.isInteger(COUPANG.id) && COUPANG.id > 0;

/** 캠페인 몇 개마다 광고 한 칸을 넣을지. 무한 스크롤로 내리는 동안 계속 넣는다. */
export const AD_EVERY = 8;

/** index번째(0부터) 캠페인 바로 뒤에 광고 칸을 넣을지 */
export function adAfter(index: number): boolean {
  return coupangEnabled && (index + 1) % AD_EVERY === 0;
}
