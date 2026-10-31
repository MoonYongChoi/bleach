"use client";

import { useCallback, useEffect, useState } from "react";
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
import { EmptyState } from "@/components/empty-state";
import {
  fetchCampaigns,
  fetchFilterOptions,
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
  const [loading, setLoading] = useState(true);
  // 불러오기에 실패했을 때 "결과 없음"과 구분해서 보여주고, 다시 시도할 수 있게 한다
  const [loadError, setLoadError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);
  // 첫 화면에서 목록이 순서대로 올라오는 등장 효과는 맨 처음 한 번만 — 필터를 바꿀 때마다 반복되면 거슬린다
  const [intro, setIntro] = useState(true);
  const favorites = useFavorites();
  // 관심 보기 중에만 관심 목록이 쿼리에 들어간다 — 그 외에는 별 누를 때마다 다시 불러올 필요 없음
  const favoriteIdsForQuery = filters.favoritesOnly ? favorites.ids : null;

  useEffect(() => {
    fetchFilterOptions().then(setFilterOptions).catch(console.error);
  }, []);

  useEffect(() => {
    // Intentional: show the skeleton immediately on every filter/search change,
    // not just the initial mount, so results re-fetching reads as "loading" to the user.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    fetchCampaigns(toQuery(search, filters, favoriteIdsForQuery ?? []))
      .then((rows) => {
        setCampaigns(rows);
        setLoadError(false);
      })
      .catch((e) => {
        console.error(e);
        setCampaigns([]);
        setLoadError(true);
      })
      .finally(() => {
        setLoading(false);
        setTimeout(() => setIntro(false), 1600);
      });
  }, [search, filters, favoriteIdsForQuery, retryKey]);

  const countFor = useCallback(
    (draft: FilterState) =>
      fetchCampaigns(toQuery(search, draft, favorites.ids)).then((rows) => rows.length),
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
          total={campaigns.length}
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
          </ul>
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
