"use client";

import { useCallback, useSyncExternalStore } from "react";

// 아직 로그인이 없어서 관심 목록은 이 기기 브라우저(localStorage)에만 저장한다.
// 로그인을 붙이면 같은 인터페이스(ids/toggle)를 유지한 채 저장소만 Supabase 테이블로 바꾸면 된다.
const STORAGE_KEY = "bleach:favorites";
const EMPTY: string[] = [];

let cache: string[] | null = null;
const listeners = new Set<() => void>();

function read(): string[] {
  if (cache) return cache;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "[]");
    cache = Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === "string") : [];
  } catch {
    cache = []; // 사생활 보호 모드 등에서 storage 접근이 막혀도 앱은 동작해야 한다
  }
  return cache;
}

function write(next: string[]) {
  cache = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // 저장 실패해도 이번 방문 동안은 메모리 값으로 유지
  }
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  // 다른 탭에서 바꾼 관심 목록도 반영
  const onStorage = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY) {
      cache = null;
      listener();
    }
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

export function useFavorites() {
  // 서버 렌더링 때는 빈 목록 — 하이드레이션 후 실제 값으로 바뀐다.
  const ids = useSyncExternalStore(subscribe, read, () => EMPTY);

  const toggle = useCallback((id: string) => {
    const current = read();
    write(current.includes(id) ? current.filter((v) => v !== id) : [id, ...current]);
  }, []);

  return { ids, isFavorite: (id: string) => ids.includes(id), toggle };
}
