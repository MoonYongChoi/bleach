"use client";

import { useState } from "react";
import {
  CoffeeIcon,
  GiftIcon,
  HouseIcon,
  PackageIcon,
  PlaneIcon,
  SmartphoneIcon,
  SparklesIcon,
  TicketIcon,
  UtensilsIcon,
  type LucideIcon,
} from "lucide-react";
import { CATEGORIES, type CategorySlug } from "@/lib/categories";

const CATEGORY_ICONS: Record<CategorySlug, LucideIcon> = {
  matjip: UtensilsIcon,
  cafe_dessert: CoffeeIcon,
  beauty: SparklesIcon,
  travel_stay: PlaneIcon,
  food_delivery: PackageIcon,
  digital: SmartphoneIcon,
  living: HouseIcon,
  culture_leisure: TicketIcon,
};

/**
 * 우리 쪽 기본 썸네일 — 원본 이미지가 없거나 열리지 않을 때(200이 아닌 응답, 이미지가 아닌 응답, 파일 삭제 등)
 * 사이트마다 제각각인 깨진 이미지 아이콘 대신 보여준다. 카테고리 색과 아이콘을 쓰고, 카테고리를 모르면
 * 선물 아이콘이 들어간 중립 타일이 된다. 디자인을 바꾸려면 이 컴포넌트와 lib/categories.ts의 색만 고치면 된다.
 */
export function DefaultThumbnail({ category }: { category: string | null }) {
  const found = category ? CATEGORIES.find((c) => c.label === category) : undefined;
  const Icon = found ? CATEGORY_ICONS[found.slug] : GiftIcon;

  return (
    <div
      aria-hidden
      className="flex size-16 shrink-0 items-center justify-center rounded-xl bg-muted text-muted-foreground"
      style={found ? { backgroundColor: found.tint, color: found.icon } : undefined}
    >
      <Icon className="size-7" strokeWidth={1.75} />
    </div>
  );
}

/** 카드 썸네일. 이미지가 없거나 불러오지 못하면 DefaultThumbnail로 바꾼다. */
export function Thumbnail({ src, category }: { src: string | null; category: string | null }) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return <DefaultThumbnail category={category} />;
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element -- external, per-domain CDN hosts; not worth next.config allowlisting yet
    <img
      src={src}
      alt=""
      loading="lazy"
      // 일부 사이트는 다른 사이트에서 불러오는 이미지를 Referer로 걸러낸다 — 출처를 보내지 않으면 걸리지 않는다
      referrerPolicy="no-referrer"
      // 404/403뿐 아니라 이미지가 아닌 응답(봇 확인 HTML 등)도 브라우저가 error로 알려준다
      onError={() => setFailed(true)}
      className="size-16 shrink-0 rounded-xl object-cover"
    />
  );
}
