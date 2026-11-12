"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { track } from "@/lib/track";

/** 페이지를 옮길 때마다 방문 기록 한 건. 관리 페이지(/admin)는 세지 않는다. */
export function PageViewTracker() {
  const pathname = usePathname();
  useEffect(() => {
    if (pathname && !pathname.startsWith("/admin")) track("page_view");
  }, [pathname]);
  return null;
}
