import { apiClient } from "./api-client";

export type RecommendationMetricsResponse = {
  model_version: string | null;
  trained_at?: string;
  metrics: Record<string, unknown> | null;
};

export async function fetchRecommendationMetrics(
  adminToken: string,
): Promise<RecommendationMetricsResponse> {
  return apiClient<RecommendationMetricsResponse>("/admin/metrics/recommendations", {
    headers: { "X-Admin-Token": adminToken },
  });
}
