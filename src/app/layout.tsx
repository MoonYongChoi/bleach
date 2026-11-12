import type { Metadata } from "next";
import { IBM_Plex_Sans_KR, Bricolage_Grotesque } from "next/font/google";
import { AdsenseScript } from "@/components/adsense-script";
import { PageViewTracker } from "@/components/page-view-tracker";
import { SITE_URL } from "@/lib/site";
import "./globals.css";

// 본문: 한글 가독성이 좋고 숫자가 단정한 IBM Plex Sans KR
const plexKr = IBM_Plex_Sans_KR({
  variable: "--font-sans",
  weight: ["400", "500", "600", "700"],
  subsets: ["latin"],
});

// 로고와 숫자(경쟁률·D-day)에만 쓰는 디스플레이 글꼴
const bricolage = Bricolage_Grotesque({
  variable: "--font-display",
  subsets: ["latin"],
});

const TITLE = "bleach — 블로그 리뷰체험 서치";
const DESCRIPTION = "다양한 블로그 체험단 모집을 한곳에서. 지역·카테고리·리뷰 채널로 거르고 경쟁률 낮은 곳부터 골라 보세요.";

// og:image는 같은 폴더의 opengraph-image.png를 Next.js가 자동으로 넣는다 (metadataBase 기준 절대 주소)
export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: TITLE,
  description: DESCRIPTION,
  applicationName: "bleach",
  openGraph: {
    type: "website",
    siteName: "bleach",
    locale: "ko_KR",
    url: "/",
    title: TITLE,
    description: DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${plexKr.variable} ${bricolage.variable} h-full antialiased`}
    >
      <head>
        <AdsenseScript />
      </head>
      <body className="min-h-full flex flex-col">
        {children}
        <PageViewTracker />
      </body>
    </html>
  );
}
