import { supabase } from "@/lib/supabase";

export interface Campaign {
  id: string;
  platform: string;
  title: string;
  region_sido: string | null;
  region_gugun: string | null;
  deadline_date: string | null;
  announce_date: string | null;
  source_url: string;
  category: string | null;
  created_at: string;
}

export type SortOption = "deadline" | "latest";

export interface CampaignFilters {
  search?: string;
  sidos?: string[];
  categories?: string[];
  sort?: SortOption;
}

export async function fetchCampaigns(filters: CampaignFilters = {}): Promise<Campaign[]> {
  let query = supabase
    .from("campaigns")
    .select("id, platform, title, region_sido, region_gugun, deadline_date, announce_date, source_url, category, created_at")
    .eq("is_active", true);

  if (filters.search) {
    query = query.ilike("title", `%${filters.search}%`);
  }
  if (filters.sidos && filters.sidos.length > 0) {
    query = query.in("region_sido", filters.sidos);
  }
  if (filters.categories && filters.categories.length > 0) {
    query = query.in("category", filters.categories);
  }

  if (filters.sort === "deadline") {
    query = query.order("deadline_date", { ascending: true, nullsFirst: false });
  } else {
    query = query.order("created_at", { ascending: false });
  }

  const { data, error } = await query.limit(100);
  if (error) throw error;
  return data ?? [];
}

export async function fetchFilterOptions(): Promise<{ sidos: string[]; categories: string[] }> {
  const { data, error } = await supabase
    .from("campaigns")
    .select("region_sido, category")
    .eq("is_active", true);
  if (error) throw error;

  const sidos = new Set<string>();
  const categories = new Set<string>();
  for (const row of data ?? []) {
    if (row.region_sido) sidos.add(row.region_sido);
    if (row.category) categories.add(row.category);
  }
  return { sidos: [...sidos].sort(), categories: [...categories].sort() };
}

export function dDay(deadlineDate: string | null): number | null {
  if (!deadlineDate) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const deadline = new Date(deadlineDate);
  deadline.setHours(0, 0, 0, 0);
  return Math.round((deadline.getTime() - today.getTime()) / 86400000);
}
