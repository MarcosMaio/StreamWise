const TOKEN_COOKIE = "streamwise_token";
const TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

export type AuthUser = {
  id: string;
  email: string;
  display_name: string;
  country_code: string;
  onboarding_complete: boolean;
  genre_ids: string[];
  streaming_provider_ids: string[];
};

export type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
};

export function setAuthToken(token: string): void {
  document.cookie = `${TOKEN_COOKIE}=${encodeURIComponent(token)}; path=/; max-age=${TOKEN_MAX_AGE_SECONDS}; SameSite=Lax`;
}

export function clearAuthToken(): void {
  document.cookie = `${TOKEN_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
}

export function getAuthTokenFromCookie(cookieHeader: string | undefined): string | null {
  if (!cookieHeader) return null;
  const match = cookieHeader
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${TOKEN_COOKIE}=`));
  if (!match) return null;
  return decodeURIComponent(match.slice(TOKEN_COOKIE.length + 1));
}

export function getAuthTokenClient(): string | null {
  if (typeof document === "undefined") return null;
  return getAuthTokenFromCookie(document.cookie);
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const { apiClient } = await import("./api-client");
  const response = await apiClient<AuthResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
  setAuthToken(response.access_token);
  return response;
}

export async function register(
  email: string,
  password: string,
  displayName: string,
): Promise<AuthResponse> {
  const { apiClient } = await import("./api-client");
  const response = await apiClient<AuthResponse>("/auth/register", {
    method: "POST",
    body: { email, password, display_name: displayName },
  });
  setAuthToken(response.access_token);
  return response;
}

export async function fetchCurrentUser(token?: string): Promise<AuthUser> {
  const { apiClient } = await import("./api-client");
  const authToken = token ?? getAuthTokenClient();
  if (!authToken) {
    throw new Error("Not authenticated");
  }
  return apiClient<AuthUser>("/users/me", { token: authToken });
}

export function logout(): void {
  clearAuthToken();
}
