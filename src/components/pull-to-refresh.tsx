"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "cn";

const TRIGGER = 64; // 이만큼(px) 당긴 뒤 놓으면 새로고침
const MAX_PULL = 96;
const RESIST = 0.5; // 손가락이 움직인 거리의 절반만 따라온다 (당기는 느낌)

/**
 * 목록 맨 위에서 아래로 당기면 위쪽에 로딩 링이 따라 내려오고, 충분히 당겼다 놓으면 onRefresh.
 * refreshing 동안 링이 돈다. 브라우저 기본 "당겨서 새로고침"(페이지를 다시 열어 조건이 초기화됨)은
 * globals.css의 overscroll-behavior-y: contain 으로 막는다.
 */
export function PullToRefresh({ refreshing, onRefresh }: { refreshing: boolean; onRefresh: () => void }) {
  const [pull, setPull] = useState(0);
  const [armed, setArmed] = useState(false); // 놓아서 새로고침을 시작했음 (refreshing이 true가 될 때까지 링 유지)
  const startY = useRef<number | null>(null);
  const pullRef = useRef(0);

  useEffect(() => {
    const onStart = (e: TouchEvent) => {
      // 맨 위에 있을 때만, 그리고 시트(필터·정렬) 같은 대화상자 안에서는 시작하지 않는다
      if (window.scrollY > 0 || e.touches.length !== 1) return;
      if ((e.target as Element | null)?.closest?.("[role=dialog]")) return;
      startY.current = e.touches[0].clientY;
    };
    const onMove = (e: TouchEvent) => {
      if (startY.current === null) return;
      const dy = e.touches[0].clientY - startY.current;
      if (dy <= 0 || window.scrollY > 0) {
        if (pullRef.current) {
          pullRef.current = 0;
          setPull(0);
        }
        return;
      }
      pullRef.current = Math.min(dy * RESIST, MAX_PULL);
      setPull(pullRef.current);
    };
    const onEnd = () => {
      if (startY.current === null) return;
      startY.current = null;
      if (pullRef.current >= TRIGGER) {
        setArmed(true);
        onRefresh();
      }
      pullRef.current = 0;
      setPull(0);
    };
    window.addEventListener("touchstart", onStart, { passive: true });
    window.addEventListener("touchmove", onMove, { passive: true });
    window.addEventListener("touchend", onEnd);
    window.addEventListener("touchcancel", onEnd);
    return () => {
      window.removeEventListener("touchstart", onStart);
      window.removeEventListener("touchmove", onMove);
      window.removeEventListener("touchend", onEnd);
      window.removeEventListener("touchcancel", onEnd);
    };
  }, [onRefresh]);

  // 새로고침이 끝나면(refreshing true → false) 링을 거둔다. 너무 빨리 끝나도 잠깐은 보이게.
  const sawRefreshing = useRef(false);
  useEffect(() => {
    if (!armed) return;
    if (refreshing) {
      sawRefreshing.current = true;
      return;
    }
    if (!sawRefreshing.current) return;
    const t = setTimeout(() => {
      sawRefreshing.current = false;
      setArmed(false);
    }, 400);
    return () => clearTimeout(t);
  }, [armed, refreshing]);

  const spinning = armed;
  const offset = spinning ? TRIGGER : pull;
  const progress = Math.min(pull / TRIGGER, 1);
  if (!spinning && pull === 0) return null;

  return (
    <div
      aria-hidden={!spinning}
      role={spinning ? "status" : undefined}
      aria-label={spinning ? "새로고침 중" : undefined}
      className={cn(
        "pointer-events-none fixed inset-x-0 top-0 z-40 flex justify-center",
        !pull && "transition-transform duration-200"
      )}
      style={{ transform: `translateY(${offset - 40}px)` }}
    >
      <span className="flex size-9 items-center justify-center rounded-full bg-card shadow-md ring-1 ring-border">
        <svg viewBox="0 0 24 24" className={cn("size-5 text-primary", spinning && "animate-spin")}>
          <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.15" strokeWidth="3" />
          <circle
            cx="12"
            cy="12"
            r="9"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            // 당긴 만큼 링이 채워지고, 놓으면 3/4 링이 돈다
            strokeDasharray={`${(spinning ? 0.75 : progress * 0.9) * 56.5} 56.5`}
            transform={`rotate(${spinning ? -90 : -90 + progress * 270} 12 12)`}
          />
        </svg>
      </span>
    </div>
  );
}
