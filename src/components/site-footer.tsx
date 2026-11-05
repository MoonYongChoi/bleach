import Link from "next/link";

const LINKS = [
  { href: "/about", label: "서비스 소개" },
  { href: "/privacy", label: "개인정보처리방침" },
  { href: "/contact", label: "문의" },
];

/** 모든 페이지 맨 아래: 소개·개인정보처리방침·문의 링크 */
export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-border px-4 py-6 text-xs text-muted-foreground">
      <nav aria-label="사이트 정보" className="flex flex-wrap gap-x-4 gap-y-2">
        {LINKS.map((link) => (
          <Link key={link.href} href={link.href} className="hover:text-foreground hover:underline">
            {link.label}
          </Link>
        ))}
      </nav>
      <p className="mt-3">
        bleach는 여러 체험단 사이트의 공개 모집 정보를 모아 보여 주는 서비스입니다. 신청은 각 체험단 사이트에서 합니다.
      </p>
    </footer>
  );
}
