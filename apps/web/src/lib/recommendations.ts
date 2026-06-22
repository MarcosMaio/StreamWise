import { apiClient } from "./api-client";
import { getAuthTokenClient } from "./auth";
import type { TitleSummary } from "./catalog";
import type { TonightContext } from "./tonight-context";

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
  context?: TonightContext | null,
): Promise<RecommendationListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  providerIds.forEach((id) => params.append("provider_ids", id));
  if (context?.time_budget) params.set("time_budget", context.time_budget);
  if (context?.mood) params.set("mood", context.mood);
  if (context?.company) params.set("company", context.company);

  return apiClient<RecommendationListResponse>(`/recommendations/for-you?${params}`, {
    token: authToken(),
  });
}
