// 사이트 공통 정보. 문의 메일은 Vercel 환경변수 NEXT_PUBLIC_CONTACT_EMAIL로 넣는다 (코드에 개인 메일을 적지 않기 위해).
export const SITE_NAME = "bleach";
export const CONTACT_EMAIL = process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "";

/** og:image 같은 절대 주소의 기준. 직접 도메인을 붙이면 NEXT_PUBLIC_SITE_URL로 바꾼다. */
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ||
  (process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : "http://localhost:3000");
