import { apiClient } from "./api-client";
import { getAuthTokenClient, type AuthUser } from "./auth";

export type GenreOption = {
  id: string;
  name: string;
};

export type ProviderOption = {
  id: string;
  name: string;
  logo_url: string | null;
};

export type OnboardingDraft = {
  genre_ids: string[];
  streaming_provider_ids: string[];
};

export type PreferencesPayload = OnboardingDraft & {
  seed_like_title_ids?: string[];
};

export const ONBOARDING_DRAFT_KEY = "streamwise_onboarding_draft";

function authToken(): string {
  const token = getAuthTokenClient();
  if (!token) {
    throw new Error("Not authenticated");
  }
  return token;
}

export async function fetchGenres(): Promise<GenreOption[]> {
  const response = await apiClient<{ items: GenreOption[] }>("/catalog/genres", {
    token: authToken(),
  });
  return response.items;
}

export async function fetchProviders(): Promise<ProviderOption[]> {
  const response = await apiClient<{ items: ProviderOption[] }>("/catalog/providers", {
    token: authToken(),
  });
  return response.items;
}

export async function savePreferences(payload: PreferencesPayload): Promise<AuthUser> {
  return apiClient<AuthUser>("/users/me/preferences", {
    method: "PUT",
    token: authToken(),
    body: payload,
  });
}

export function saveOnboardingDraft(draft: OnboardingDraft): void {
  sessionStorage.setItem(ONBOARDING_DRAFT_KEY, JSON.stringify(draft));
}

export function loadOnboardingDraft(): OnboardingDraft | null {
  const raw = sessionStorage.getItem(ONBOARDING_DRAFT_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as OnboardingDraft;
  } catch {
    return null;
  }
}

export function clearOnboardingDraft(): void {
  sessionStorage.removeItem(ONBOARDING_DRAFT_KEY);
}

export function toggleSelection(ids: string[], id: string): string[] {
  return ids.includes(id) ? ids.filter((item) => item !== id) : [...ids, id];
}
