import { apiClient } from "./api-client";
import { fetchCurrentUser, getAuthTokenClient, type AuthUser } from "./auth";
import type { TitleListResponse, TitleSummary } from "./catalog";
  provider_id: string;
  provider_name: string;
  score: number;
};

export type StreamingAffinityResponse = {
  providers: StreamingAffinity[];
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
