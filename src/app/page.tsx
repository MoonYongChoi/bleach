"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SiteHeader } from "@/components/site-header";
import { QuickFilters, ResultsBar } from "@/components/quick-filters";
import {
  FilterSheet,
  EMPTY_FILTER_STATE,
  type FilterSection,
  type FilterState,
} from "@/components/filter-sheet";
import { SortSheet } from "@/components/sort-sheet";
import { PlatformRequestSheet } from "@/components/platform-request-sheet";
import { CampaignCard, CampaignCardSkeleton } from "@/components/campaign-card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { loadCampaignCount, loadCampaignPage, loadFilterOptions } from "@/lib/api";
import {
  PAGE_SIZE,
  type Campaign,
  type CampaignFilters,
  type FilterOptions,
} from "@/lib/campaigns";
import { useFavorites } from "@/lib/favorites";

function toQuery(search: string, f: FilterState, favoriteIds: string[]): CampaignFilters {
  return {
    search,
    sidos: f.sidos,
    guguns: f.guguns,
    categories: f.categories,
    platforms: f.platforms,
    types: f.types,
    channels: f.channels,
    applyRate: f.applyRate ?? undefined,
    ids: f.favoritesOnly ? favoriteIds : undefined,
    sort: f.sort,
    includeOpenEnded: f.includeOpenEnded,
  };
}

export default function Home() {
  // 입력 중인 글자(draft)와 실제로 검색에 쓰이는 글자(search)를 나눈다 — 엔터를 눌러야 search가 바뀐다
  const [searchDraft, setSearchDraft] = useState("");
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTER_STATE);
  const [filterSection, setFilterSection] = useState<FilterSection | null>(null);
  const [sortOpen, setSortOpen] = useState(false);
  const [requestOpen, setRequestOpen] = useState(false);
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    sidos: [],
    guguns: {},
    categories: [],
    types: [],
    channels: [],
  });
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  // 무한 스크롤: 스크롤이 끝에 가까워지면 다음 묶음을 이어 붙인다
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadMoreError, setLoadMoreError] = useState(false);
  const nextPageRef = useRef(1);
  // 조건(검색·필터)이 바뀔 때마다 올라간다 — 이전 조건의 늦은 응답이 새 목록을 덮어쓰지 못하게 버리는 용도
  const generationRef = useRef(0);
  const sentinelRef = useRef<HTMLDivElement>(null);
  // 불러오기에 실패했을 때 "결과 없음"과 구분해서 보여주고, 다시 시도할 수 있게 한다
  const [loadError, setLoadError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);
  // 첫 화면에서 목록이 순서대로 올라오는 등장 효과는 맨 처음 한 번만 — 필터를 바꿀 때마다 반복되면 거슬린다
  const [intro, setIntro] = useState(true);
  const favorites = useFavorites();
  // 관심 보기 중에만 관심 목록이 쿼리에 들어간다 — 그 외에는 별 누를 때마다 다시 불러올 필요 없음
  const favoriteIdsForQuery = filters.favoritesOnly ? favorites.ids : null;

  useEffect(() => {
    loadFilterOptions().then(setFilterOptions).catch(console.error);
  }, []);

  const query = useMemo(
    () => toQuery(search, filters, favoriteIdsForQuery ?? []),
    [search, filters, favoriteIdsForQuery]
  );

  useEffect(() => {
    const generation = ++generationRef.current;
    nextPageRef.current = 1;
    window.scrollTo({ top: 0 });
    // Intentional: show the skeleton immediately on every filter/search change,
    // not just the initial mount, so results re-fetching reads as "loading" to the user.
    /* eslint-disable react-hooks/set-state-in-effect */
    setLoading(true);
    setLoadMoreError(false);
    /* eslint-enable react-hooks/set-state-in-effect */
    Promise.all([loadCampaignPage(query, 0), loadCampaignCount(query)])
      .then(([rows, count]) => {
        if (generation !== generationRef.current) return;
        setCampaigns(rows);
        setTotal(count);
        setHasMore(rows.length >= PAGE_SIZE && rows.length < count);
        setLoadError(false);
      })
      .catch((e) => {
        if (generation !== generationRef.current) return;
        console.error(e);
        setCampaigns([]);
        setTotal(0);
        setHasMore(false);
        setLoadError(true);
      })
      .finally(() => {
        if (generation !== generationRef.current) return;
        setLoading(false);
        setTimeout(() => setIntro(false), 1600);
      });
  }, [query, retryKey]);

  const loadMore = useCallback(() => {
    if (loading || loadingMore || !hasMore) return;
    const generation = generationRef.current;
    setLoadingMore(true);
    setLoadMoreError(false);
    loadCampaignPage(query, nextPageRef.current)
      .then((rows) => {
        if (generation !== generationRef.current) return;
        nextPageRef.current += 1;
        // 불러오는 사이 목록이 바뀌어 같은 캠페인이 두 번 올 수 있어 id로 걸러 붙인다
        setCampaigns((prev) => {
          const seen = new Set(prev.map((c) => c.id));
          return [...prev, ...rows.filter((c) => !seen.has(c.id))];
        });
        setHasMore(rows.length >= PAGE_SIZE);
      })
      .catch((e) => {
        if (generation !== generationRef.current) return;
        console.error(e);
        setLoadMoreError(true);
      })
      .finally(() => {
        if (generation === generationRef.current) setLoadingMore(false);
      });
  }, [loading, loadingMore, hasMore, query]);

  // 목록 맨 아래 눈에 안 보이는 표시가 화면 근처(600px 앞)에 오면 다음 묶음을 받는다.
  // 묶음이 붙을 때마다 다시 관찰해서, 화면이 넓어 표시가 계속 보이는 경우에도 이어서 채운다.
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el || !hasMore || loadMoreError) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) loadMore();
      },
      { rootMargin: "600px 0px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore, loadMore, loadMoreError, campaigns.length]);

  const countFor = useCallback(
    (draft: FilterState) => loadCampaignCount(toQuery(search, draft, favorites.ids)),
    [search, favorites.ids]
  );

  function resetFilters() {
    setSearchDraft("");
    setSearch("");
    setFilters((f) => ({ ...EMPTY_FILTER_STATE, sort: f.sort, includeOpenEnded: f.includeOpenEnded }));
  }

  const noFavoritesYet = filters.favoritesOnly && favorites.ids.length === 0;

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-md flex-1 flex-col bg-card sm:shadow-[0_0_0_1px_var(--border)]">
      <div className="sticky top-0 z-10 bg-card/90 backdrop-blur-md">
        <SiteHeader draft={searchDraft} onDraftChange={setSearchDraft} onSubmit={setSearch} />
        <QuickFilters
          value={filters}
          favoriteCount={favorites.ids.length}
          onOpenSection={setFilterSection}
          onToggleFavorites={() => setFilters((f) => ({ ...f, favoritesOnly: !f.favoritesOnly }))}
        />
        {/* 불러오는 동안 흐르는 얇은 막대 — 자리는 항상 잡아 두어 나타날 때 화면이 밀리지 않는다 */}
        <div className="h-0.5 overflow-hidden bg-transparent" aria-hidden={!loading}>
          {loading && (
            <div role="progressbar" aria-label="체험단 목록 불러오는 중" className="bar-slide h-full w-1/4 rounded-full bg-primary" />
          )}
        </div>
        <ResultsBar
          total={total}
          loading={loading || loadError}
          value={filters}
          onOpenSort={() => setSortOpen(true)}
          onToggleOpenEnded={() => setFilters((f) => ({ ...f, includeOpenEnded: !f.includeOpenEnded }))}
          onReset={resetFilters}
        />
      </div>

      <main className="flex flex-1 flex-col" aria-busy={loading}>
        {loading ? (
          <ul className="divide-y divide-border">
            {Array.from({ length: 5 }).map((_, i) => (
              <CampaignCardSkeleton key={i} />
            ))}
          </ul>
        ) : loadError ? (
          <EmptyState variant="error" onReset={() => setRetryKey((k) => k + 1)} />
        ) : noFavoritesYet ? (
          <EmptyState
            variant="favorites"
            onReset={() => setFilters((f) => ({ ...f, favoritesOnly: false }))}
          />
        ) : campaigns.length === 0 ? (
          <EmptyState onReset={resetFilters} />
        ) : (
          <ul className="divide-y divide-border">
            {campaigns.map((campaign, i) => (
              <CampaignCard
                key={campaign.id}
                campaign={campaign}
                index={i}
                intro={intro}
                favorite={favorites.isFavorite(campaign.id)}
                onToggleFavorite={() => favorites.toggle(campaign.id)}
              />
            ))}
            {loadingMore && [0, 1].map((i) => <CampaignCardSkeleton key={`more-${i}`} />)}
          </ul>
        )}

        {/* 무한 스크롤 끝 표시: 다음 묶음이 있으면 눈에 안 보이는 감시 칸, 실패하면 다시 시도, 다 불러왔으면 마무리 문구 */}
        {!loading && !loadError && campaigns.length > 0 && (
          <>
            {hasMore && !loadMoreError && <div ref={sentinelRef} className="h-px" aria-hidden />}
            {loadMoreError && (
              <div className="flex flex-col items-center gap-2 px-4 py-6 text-center" role="alert">
                <p className="text-sm text-muted-foreground">다음 체험단을 불러오지 못했어요.</p>
                <Button variant="outline" size="sm" onClick={loadMore}>
                  다시 시도
                </Button>
              </div>
            )}
            {!hasMore && (
              <p className="px-4 py-6 text-center text-xs text-muted-foreground">
                마지막까지 봤어요 · 총 <b className="font-display font-bold tabular-nums text-foreground">{total.toLocaleString()}</b>개
              </p>
            )}
          </>
        )}

        {!loading && !loadError && (
          <button
            onClick={() => setRequestOpen(true)}
            className="m-4 rounded-2xl bg-primary/5 px-4 py-4 text-center text-sm text-muted-foreground transition-colors hover:bg-primary/10 active:scale-[0.99]"
          >
            찾는 체험단 사이트가 없나요? <span className="font-semibold text-primary">추가 요청하기</span>
          </button>
        )}
      </main>

      <FilterSheet
        open={filterSection !== null}
        onOpenChange={(open) => !open && setFilterSection(null)}
        initialSection={filterSection ?? "type"}
        options={filterOptions}
        value={filters}
        onApply={setFilters}
        countFor={countFor}
        onRequestPlatform={() => {
          setFilterSection(null);
          setRequestOpen(true);
        }}
      />
      <PlatformRequestSheet open={requestOpen} onOpenChange={setRequestOpen} />
      <SortSheet
        open={sortOpen}
        onOpenChange={setSortOpen}
        value={filters.sort}
        onChange={(sort) => setFilters((f) => ({ ...f, sort }))}
        includeOpenEnded={filters.includeOpenEnded}
        onToggleOpenEnded={() => setFilters((f) => ({ ...f, includeOpenEnded: !f.includeOpenEnded }))}
      />
    </div>
  );
}
