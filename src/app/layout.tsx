import type { Metadata } from "next";
import { IBM_Plex_Sans_KR, Bricolage_Grotesque } from "next/font/google";
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

export const metadata: Metadata = {
  title: "BLEACH — 블로그 체험단 서치",
  description: "흩어진 블로그 체험단 정보를 한곳에 모아보는 서비스",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="ko"
      className={`${plexKr.variable} ${bricolage.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
