"use client";

import { COUPANG, coupangEnabled } from "@/lib/ads";

// 쿠팡이 준 배너 코드 그대로. 스크립트가 배너를 어떻게 끼워 넣든(document.write 등) 우리 페이지에 영향이 없게
// 별도 문서(iframe srcdoc) 안에서 돌린다.
const SRC_DOC = `<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;overflow:hidden;background:transparent}</style></head><body>
<script src="https://ads-partners.coupang.com/g.js"></script>
<script>new PartnersCoupang.G(${JSON.stringify({
  id: COUPANG.id,
  template: COUPANG.template,
  trackingCode: COUPANG.trackingCode,
  width: String(COUPANG.width),
  height: String(COUPANG.height),
  tsource: "",
})});</script>
</body></html>`;

/**
 * 목록 사이 쿠팡 파트너스 배너 한 칸. "광고" 표시와 수수료 고지(공정위 추천·보증 지침)를 함께 붙인다.
 * 폭 320px — 가장 작은 폰(360px)에서도 좌우 여백 안에 들어간다.
 */
export function CoupangSlot() {
  if (!coupangEnabled) return null;
  return (
    <li aria-label="광고" className="list-none bg-muted/40 px-4 py-1.5">
      <div className="flex justify-center">
        <iframe
          title="쿠팡 파트너스 광고"
          srcDoc={SRC_DOC}
          width={COUPANG.width}
          height={COUPANG.height}
          loading="lazy"
          scrolling="no"
          className="block max-w-full border-0"
        />
      </div>
      {/* "광고" 표시 + 수수료 고지(공정위 추천·보증 지침)를 한 줄로 — 카드 한 장 높이에 가깝게 */}
      <p className="mt-1 truncate text-center text-[10.5px] leading-tight text-muted-foreground">
        <b className="font-semibold">광고</b> · 쿠팡 파트너스 활동으로 일정액의 수수료를 제공받습니다
      </p>
    </li>
  );
}
