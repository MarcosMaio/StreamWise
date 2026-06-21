import { apiClient } from "./api-client";
import { getAuthTokenClient } from "./auth";
import type { TitleSummary } from "./catalog";

export type RecommendationItem = TitleSummary & {
  score: number;
  reason_tags?: string[];
};

export type RecommendationListResponse = {
  items: RecommendationItem[];
  fallback_used: boolean;
};

function authToken(): string {
  const token = getAuthTokenClient();
  if (!token) {
    throw new Error("Not authenticated");
  }
  return token;
}

export async function fetchForYouFeed(
  limit = 20,
  providerIds: string[] = [],
): Promise<RecommendationListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  providerIds.forEach((id) => params.append("provider_ids", id));
  return apiClient<RecommendationListResponse>(`/recommendations/for-you?${params}`, {
    token: authToken(),
  });
}
