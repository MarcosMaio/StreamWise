import { apiClient } from "./api-client";
import { fetchCurrentUser, getAuthTokenClient, type AuthUser } from "./auth";
import type { TitleListResponse, TitleSummary } from "./catalog";

export type StreamingAffinity = {
  provider_id: string;
  provider_name: string;
  score: number;
};

export type StreamingAffinityResponse = {
  providers: StreamingAffinity[];
};

export type ImportWatchlistResult = {
  imported: number;
  skipped: number;
  missing_tmdb_ids: number[];
};

export type ContentFilter = {
  blocked_genre_ids: string[];
  max_certification: string | null;
};

function authToken(): string {
  const token = getAuthTokenClient();
  if (!token) {
    throw new Error("Not authenticated");
  }
  return token;
}

export async function fetchUserProfile(): Promise<AuthUser> {
  return fetchCurrentUser();
}

export async function fetchUserLikes(limit = 50): Promise<TitleListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiClient<TitleListResponse>(`/users/me/likes?${params}`, {
    token: authToken(),
  });
}

export async function fetchUserWatchlist(limit = 50): Promise<TitleListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiClient<TitleListResponse>(`/users/me/watchlist?${params}`, {
    token: authToken(),
  });
}

export async function fetchStreamingAffinity(): Promise<StreamingAffinityResponse> {
  return apiClient<StreamingAffinityResponse>("/users/me/affinity", {
    token: authToken(),
  });
}

export type ContinueWatchingItem = TitleSummary & {
  season: number;
  episode: number;
};

export type ContinueWatchingResponse = {
  items: ContinueWatchingItem[];
  total: number;
};

export async function fetchContinueWatching(limit = 20): Promise<ContinueWatchingResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiClient<ContinueWatchingResponse>(`/users/me/continue-watching?${params}`, {
    token: authToken(),
  });
}

export async function importWatchlistCsv(file: File): Promise<ImportWatchlistResult> {
  const formData = new FormData();
  formData.append("file", file);
  const token = authToken();
  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}/users/me/import/csv`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Import failed");
  }
  return response.json();
}

export async function fetchContentFilter(): Promise<ContentFilter> {
  return apiClient<ContentFilter>("/users/me/content-filter", {
    token: authToken(),
  });
}

export async function updateContentFilter(data: ContentFilter): Promise<ContentFilter> {
  return apiClient<ContentFilter>("/users/me/content-filter", {
    method: "PUT",
    token: authToken(),
    body: JSON.stringify(data),
  });
}
