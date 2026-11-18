import { supabase } from "@/lib/supabase";

// 수집기가 받아 둔 썸네일(thumb_cache)을 이미지로 내준다. 방문자 브라우저가 원본을 직접 못 받는 사이트용(모두블로그).
// 저장된 주소만 내주므로 아무 주소나 대신 받아 주는 프록시가 되지 않는다.
export async function GET(request: Request) {
  const url = new URL(request.url).searchParams.get("u");
  if (!url || url.length > 500) return new Response(null, { status: 400 });

  const { data, error } = await supabase.from("thumb_cache").select("content_type, bytes").eq("url", url).maybeSingle();
  if (error || !data) return new Response(null, { status: 404, headers: { "cache-control": "public, s-maxage=600" } });

  // PostgREST는 bytea를 "\\x" + 16진수 문자열로 준다
  const hex = String(data.bytes).replace(/^\\x/, "");
  const body = Buffer.from(hex, "hex");
  return new Response(body, {
    headers: {
      "content-type": data.content_type,
      // 같은 주소의 그림은 바뀌지 않는다 — CDN과 브라우저가 오래 들고 있게
      "cache-control": "public, max-age=86400, s-maxage=604800, immutable",
    },
  });
}
