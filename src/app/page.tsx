"use client";

import { useEffect, useState } from "react";
import { SiteHeader } from "@/components/site-header";
import { QuickFilters } from "@/components/quick-filters";
import { FilterSheet, EMPTY_FILTER_STATE, type FilterState } from "@/components/filter-sheet";
import { CampaignCard, CampaignCardSkeleton } from "@/components/campaign-card";
import { EmptyState } from "@/components/empty-state";
import { fetchCampaigns, fetchFilterOptions, type Campaign } from "@/lib/campaigns";

type SheetTab = "region" | "category" | "vendor" | "applyRate";

export default function Home() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTER_STATE);
  const [sheetTab, setSheetTab] = useState<SheetTab | null>(null);
  const [filterOptions, setFilterOptions] = useState<{
    sidos: string[];
    categories: string[];
    vendors: string[];
  }>({ sidos: [], categories: [], vendors: [] });
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);

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
    fetchCampaigns({
      search: debouncedSearch,
      sidos: filters.sidos,
      categories: filters.categories,
      vendors: filters.vendors,
      applyRate: filters.applyRate ?? undefined,
      sort: filters.sort,
    })
      .then(setCampaigns)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [debouncedSearch, filters]);

  function resetFilters() {
    setSearch("");
    setFilters(EMPTY_FILTER_STATE);
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-md flex-1 flex-col bg-background">
      <SiteHeader search={search} onSearchChange={setSearch} />
      <QuickFilters
        value={filters}
        onOpenTab={(tab) => setSheetTab(tab)}
        onToggleSort={() =>
          setFilters((f) => ({ ...f, sort: f.sort === "deadline" ? "latest" : "deadline" }))
        }
      />

      <main className="flex flex-1 flex-col gap-3 overflow-y-auto p-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <CampaignCardSkeleton key={i} />)
        ) : campaigns.length === 0 ? (
          <EmptyState onReset={resetFilters} />
        ) : (
          campaigns.map((campaign) => <CampaignCard key={campaign.id} campaign={campaign} />)
        )}
      </main>

      <FilterSheet
        open={sheetTab !== null}
        onOpenChange={(open) => !open && setSheetTab(null)}
        initialTab={sheetTab ?? "region"}
        sidoOptions={filterOptions.sidos}
        categoryOptions={filterOptions.categories}
        vendorOptions={filterOptions.vendors}
        value={filters}
        onApply={setFilters}
      />
    </div>
  );
}
