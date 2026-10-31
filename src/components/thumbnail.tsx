"use client";

import { useState } from "react";

/**
 * 카드 썸네일. 주소가 없거나 이미지가 열리지 않으면(사이트에서 파일을 지운 경우 등) 브라우저의
 * 깨진 이미지 아이콘(사파리는 "?") 대신 회색 칸을 보여준다.
 */
export function Thumbnail({ src }: { src: string | null }) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return <div className="size-16 shrink-0 rounded-xl bg-muted" />;
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element -- external, per-domain CDN hosts; not worth next.config allowlisting yet
    <img
      src={src}
      alt=""
      loading="lazy"
      // 일부 사이트는 다른 사이트에서 불러오는 이미지를 Referer로 걸러낸다 — 출처를 보내지 않으면 걸리지 않는다
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
      className="size-16 shrink-0 rounded-xl object-cover"
    />
  );
}
