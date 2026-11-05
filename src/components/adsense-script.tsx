import { ADSENSE_CLIENT, scriptEnabled } from "@/lib/ads";

/**
 * AdSense 코드. 서버가 그린 HTML의 <head>에 그대로 들어가야 AdSense의 사이트 연결·소유 확인이 찾을 수 있다
 * (next/script의 afterInteractive는 브라우저에서 나중에 넣어서 확인 크롤러가 못 볼 수 있다).
 */
export function AdsenseScript() {
  if (!scriptEnabled) return null;
  return (
    <script
      async
      src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${ADSENSE_CLIENT}`}
      crossOrigin="anonymous"
    />
  );
}
