"use client";

import { useSyncExternalStore } from "react";
import { todayKst } from "@/lib/campaigns";

const noop = () => () => {};

/**
 * 오늘 날짜(KST, "YYYY-MM-DD"). 서버에서 미리 그릴 때와 하이드레이션 첫 렌더에서는 null —
 * 캐시된 HTML이 하루 지나도 "D-1"처럼 틀린 날짜가 남지 않게 D-day는 브라우저에서만 계산한다.
 */
export function useTodayKst(): string | null {
  return useSyncExternalStore(noop, todayKst, () => null);
}
