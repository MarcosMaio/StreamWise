import { apiClient } from "./api-client";
import { getAuthTokenClient } from "./auth";

export type StreamingProviderBadge = {
  id: string;
  name: string;
  logo_url: string | null;
  availability_type: string;
};

export type TitleSummary = {
  id: string;
  tmdb_id: number;
  type: "movie" | "series";
  title: string;
  overview: string | null;
  release_date: string | null;
  poster_url: string | null;
  streamwise_avg_rating: number | null;
  like_count: number;
  genres: string[];
  streaming_providers: StreamingProviderBadge[];
};

export type TitleListResponse = {
  items: TitleSummary[];
  total: number;
  stale_data?: boolean;
  availability_note?: string | null;
};

export type TitleDetail = TitleSummary & {
  tmdb_popularity: number;
  is_trending: boolean;
  certification?: string | null;
  availability_note?: string | null;
  rent_providers?: StreamingProviderBadge[];
  buy_providers?: StreamingProviderBadge[];
};

export type CatalogFilters = {
  providerIds?: string[];
  genreIds?: string[];
};

export type SearchFilters = CatalogFilters & {
  type?: "movie" | "series";
  duration?: "short" | "long";
  mood?: "funny" | "intense" | "cozy" | "thoughtful";
};

function authToken(): string {
  const token = getAuthTokenClient();
  if (!token) {
    throw new Error("Not authenticated");
  }
  return token;
}

function appendFilterParams(params: URLSearchParams, filters?: CatalogFilters) {
  filters?.providerIds?.forEach((id) => params.append("provider_ids", id));
  filters?.genreIds?.forEach((id) => params.append("genre_ids", id));
}

export async function fetchTrending(
  type: "movie" | "series" | "all" = "all",
  limit = 20,
  filters?: CatalogFilters,
): Promise<TitleListResponse> {
  const params = new URLSearchParams({ type, limit: String(limit) });
  appendFilterParams(params, filters);
  return apiClient<TitleListResponse>(`/catalog/trending?${params}`, {
    token: authToken(),
  });
}

export async function fetchNewReleases(
  limit = 20,
  filters?: CatalogFilters,
): Promise<TitleListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  appendFilterParams(params, filters);
  return apiClient<TitleListResponse>(`/catalog/new?${params}`, {
    token: authToken(),
  });
}

export async function fetchTitleDetail(titleId: string): Promise<TitleDetail> {
  return apiClient<TitleDetail>(`/titles/${titleId}`, {
    token: authToken(),
  });
}

export async function fetchSimilarTitles(
  titleId: string,
  limit = 20,
): Promise<TitleListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiClient<TitleListResponse>(`/titles/${titleId}/similar?${params}`, {
    token: authToken(),
  });
}

export async function searchCatalog(
  query: string,
  limit = 20,
  filters?: SearchFilters,
): Promise<TitleListResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  appendFilterParams(params, filters);
  if (filters?.type) params.set("type", filters.type);
  if (filters?.duration) params.set("duration", filters.duration);
  if (filters?.mood) params.set("mood", filters.mood);
  return apiClient<TitleListResponse>(`/catalog/search?${params}`, {
    token: authToken(),
  });
}

export type CatalogChangeItem = {
  id: string;
  title_id: string;
  title_name: string;
  provider_name: string;
  change_type: "enter" | "leave";
  availability_type: string;
  detected_at: string;
};

export type CatalogChangeListResponse = {
  items: CatalogChangeItem[];
  total: number;
};

export async function fetchCatalogChanges(limit = 20): Promise<CatalogChangeListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiClient<CatalogChangeListResponse>(`/catalog/changes?${params}`, {
    token: authToken(),
  });
}
