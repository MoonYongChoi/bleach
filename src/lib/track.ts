// 이용 기록 보내기 (브라우저 전용). 페이지 방문·검색·필터·체험단 클릭을 /api/log 로 보내고, 서버가 Supabase에 쌓는다.
// IP·쿠키·로그인 정보는 보내지 않는다. session은 탭마다 새로 만드는 임의 값(sessionStorage)이라 탭을 닫으면 사라진다.

export type TrackEvent = "page_view" | "search" | "filter" | "click";

const SESSION_KEY = "bleach_sid";

function sessionId(): string {
  try {
    const saved = sessionStorage.getItem(SESSION_KEY);
    if (saved) return saved;
    const id = crypto.randomUUID().replace(/-/g, "").slice(0, 20);
    sessionStorage.setItem(SESSION_KEY, id);
    return id;
  } catch {
    return "nostorage" + Math.random().toString(36).slice(2, 12);
  }
}

/** 다른 사이트에서 들어왔으면 그 도메인만 (경로·검색어는 버린다) */
function referrerHost(): string {
  try {
    const ref = document.referrer ? new URL(document.referrer) : null;
    return ref && ref.host !== location.host ? ref.host : "";
  } catch {
    return "";
  }
}

export function track(event: TrackEvent, data: Record<string, unknown> = {}): void {
  if (typeof window === "undefined") return;
  const body = JSON.stringify({
    event,
    session: sessionId(),
    path: location.pathname,
    referrer: event === "page_view" ? referrerHost() : "",
    data,
  });
  try {
    if (navigator.sendBeacon?.("/api/log", new Blob([body], { type: "application/json" }))) return;
  } catch {
    // sendBeacon이 없거나 막히면 아래 fetch로
  }
  fetch("/api/log", { method: "POST", body, keepalive: true, headers: { "content-type": "application/json" } }).catch(
    () => {}
  );
}
