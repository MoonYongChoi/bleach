"use client";

import { useEffect, useRef } from "react";
import { ADSENSE_CLIENT, ADSENSE_LAYOUT_KEY, ADSENSE_SLOT, adsEnabled } from "@/lib/ads";

declare global {
  interface Window {
    adsbygoogle?: unknown[];
  }
}

// 개발 모드의 이중 실행이나 다시 그려질 때 같은 칸에 광고를 두 번 요청하면 AdSense가 오류를 낸다
const requested = new WeakSet<Element>();

/**
 * 목록 사이에 들어가는 구글 광고 한 칸 (피드형).
 * - "광고" 표시를 붙여 콘텐츠와 구분하고, 별(관심)·카드와 닿지 않게 위아래 여백을 둔다 (실수 클릭 유도 금지 정책).
 * - 자리를 미리 잡아 두어 광고가 늦게 떠도 목록이 밀리지 않게 하고, 광고가 채워지지 않으면(unfilled) 칸째 숨긴다.
 */
export function AdSlot() {
  const ref = useRef<HTMLModElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!adsEnabled || !el || requested.has(el)) return;
    requested.add(el);
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch (e) {
      console.warn("adsbygoogle push failed", e);
    }
  }, []);

  if (!adsEnabled) return null;

  const feed = ADSENSE_LAYOUT_KEY
    ? { "data-ad-format": "fluid", "data-ad-layout-key": ADSENSE_LAYOUT_KEY }
    : { "data-ad-format": "auto", "data-full-width-responsive": "true" };

  return (
    <li
      aria-label="광고"
      className="list-none bg-muted/40 px-4 py-4 [&:has(ins[data-ad-status=unfilled])]:hidden"
    >
      <p className="mb-2 text-[11px] font-medium text-muted-foreground">광고</p>
      <ins
        ref={ref}
        className="adsbygoogle block min-h-24"
        style={{ display: "block" }}
        data-ad-client={ADSENSE_CLIENT}
        data-ad-slot={ADSENSE_SLOT}
        {...feed}
      />
    </li>
  );
}
