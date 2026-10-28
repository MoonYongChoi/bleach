// BLEACH 공통 카테고리 체계 — 레뷰/파블로/리뷰노트의 제각각인 카테고리명을
// 아래 8개 표준 슬러그로 매핑해서 저장/필터링한다.

export type CategorySlug =
  | "matjip"
  | "cafe_dessert"
  | "beauty"
  | "travel_stay"
  | "food_delivery"
  | "digital"
  | "living"
  | "culture_leisure";

export interface Category {
  slug: CategorySlug;
  label: string;
  tint: string; // 아이콘 타일 배경
  icon: string; // 아이콘 색상
}

export const CATEGORIES: Category[] = [
  { slug: "matjip", label: "맛집", tint: "#FDECE8", icon: "#D1572B" },
  { slug: "cafe_dessert", label: "카페·디저트", tint: "#F4EADF", icon: "#8B5A2B" },
  { slug: "beauty", label: "뷰티", tint: "#FBE8F3", icon: "#C23B8E" },
  { slug: "travel_stay", label: "여행·숙박", tint: "#E6F0FB", icon: "#1E6FA8" },
  { slug: "food_delivery", label: "식품·배송", tint: "#FDF3DC", icon: "#A5730A" },
  { slug: "digital", label: "디지털", tint: "#ECECEF", icon: "#4B5153" },
  { slug: "living", label: "생활", tint: "#E6F5EE", icon: "#2F8A62" },
  { slug: "culture_leisure", label: "문화·여가", tint: "#F1EAFB", icon: "#6D4FA0" },
];

// 각 플랫폼에서 수집한 원본 카테고리 텍스트 → 표준 슬러그 매핑.
// 스크래퍼가 campaigns.category 컬럼에 적재하기 전에 이 테이블로 정규화한다.
export const CATEGORY_ALIASES: Record<string, CategorySlug> = {
  // 레뷰
  "맛집": "matjip",
  "식품": "food_delivery",
  "여행": "travel_stay",
  "숙박": "travel_stay",
  "디지털": "digital",
  "뷰티": "beauty",
  "문화": "culture_leisure",
  "생활": "living",
  "패션": "beauty",
  "도서": "culture_leisure",
  "서비스": "living",
  "반려동물": "living",
  "유아동": "living",
  "배달": "matjip",
  "테이크아웃": "matjip",

  // 파블로
  "여가": "culture_leisure",
  "운동": "culture_leisure",
  "배송": "food_delivery",
  "출장": "living",
  "방문": "living",

  // 공통 catch-all (리뷰노트는 대부분 "기타"로만 내려옴 — 제목/오퍼 텍스트로 추가 분류 필요)
  "기타": "living",
};

export function normalizeCategory(raw: string | null | undefined): CategorySlug | null {
  if (!raw) return null;
  return CATEGORY_ALIASES[raw.trim()] ?? null;
}

export function getCategory(slug: CategorySlug): Category {
  const found = CATEGORIES.find((c) => c.slug === slug);
  if (!found) throw new Error(`Unknown category slug: ${slug}`);
  return found;
}
