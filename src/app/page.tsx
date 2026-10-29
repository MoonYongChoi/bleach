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
  };
}

export default function Home() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTER_STATE);
  const [filterSection, setFilterSection] = useState<FilterSection | null>(null);
  const [sortOpen, setSortOpen] = useState(false);
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    sidos: [],
    guguns: {},
    categories: [],
    types: [],
    channels: [],
  });
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const favorites = useFavorites();
  // 관심 보기 중에만 관심 목록이 쿼리에 들어간다 — 그 외에는 별 누를 때마다 다시 불러올 필요 없음
  const favoriteIdsForQuery = filters.favoritesOnly ? favorites.ids : null;

  useEffect(() => {
    fetchFilterOptions().then(setFilterOptions).catch(console.error);
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timeout);
  }, [search]);

  useEffect(() => {
    // Intentional: show the skeleton immediately on every filter/search change,
    // not just the initial mount, so results re-fetching reads as "loading" to the user.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    fetchCampaigns(toQuery(debouncedSearch, filters, favoriteIdsForQuery ?? []))
      .then(setCampaigns)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [debouncedSearch, filters, favoriteIdsForQuery]);

  const countFor = useCallback(
    (draft: FilterState) =>
      fetchCampaigns(toQuery(debouncedSearch, draft, favorites.ids)).then((rows) => rows.length),
    [debouncedSearch, favorites.ids]
  );

  function resetFilters() {
    setSearch("");
    setFilters((f) => ({ ...EMPTY_FILTER_STATE, sort: f.sort }));
  }

  const noFavoritesYet = filters.favoritesOnly && favorites.ids.length === 0;

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-md flex-1 flex-col bg-background">
      <div className="sticky top-0 z-10 bg-background">
        <SiteHeader search={search} onSearchChange={setSearch} />
        <QuickFilters
          value={filters}
          favoriteCount={favorites.ids.length}
          onOpenSection={setFilterSection}
          onToggleFavorites={() => setFilters((f) => ({ ...f, favoritesOnly: !f.favoritesOnly }))}
        />
        <ResultsBar
          total={campaigns.length}
          loading={loading}
          value={filters}
          onOpenSort={() => setSortOpen(true)}
          onReset={resetFilters}
        />
      </div>

      <main className="flex flex-1 flex-col gap-3 p-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <CampaignCardSkeleton key={i} />)
        ) : noFavoritesYet ? (
          <EmptyState
            variant="favorites"
            onReset={() => setFilters((f) => ({ ...f, favoritesOnly: false }))}
          />
        ) : campaigns.length === 0 ? (
          <EmptyState onReset={resetFilters} />
        ) : (
          campaigns.map((campaign) => (
            <CampaignCard
              key={campaign.id}
              campaign={campaign}
              favorite={favorites.isFavorite(campaign.id)}
              onToggleFavorite={() => favorites.toggle(campaign.id)}
            />
          ))
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
      />
      <SortSheet
        open={sortOpen}
        onOpenChange={setSortOpen}
        value={filters.sort}
        onChange={(sort) => setFilters((f) => ({ ...f, sort }))}
      />
    </div>
  );
}
