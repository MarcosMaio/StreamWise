import { apiClient } from "./api-client";
import { getAuthTokenClient } from "./auth";
import type { TitleSummary } from "./catalog";

export type EventType = "like" | "dislike" | "rating" | "watchlist" | "watched";

export type InteractionResponse = {
  id: string;
  event_type: EventType;
  title: TitleSummary;
};

function authToken(): string {
  const token = getAuthTokenClient();
  if (!token) {
    throw new Error("Not authenticated");
  }
  return token;
}

export async function recordInteraction(
  titleId: string,
  eventType: EventType,
  rating?: number,
): Promise<InteractionResponse> {
  const body: { event_type: EventType; rating?: number } = { event_type: eventType };
  if (eventType === "rating" && rating !== undefined) {
    body.rating = rating;
  }

  return apiClient<InteractionResponse>(`/titles/${titleId}/interactions`, {
    method: "POST",
    token: authToken(),
    body,
  });
}
