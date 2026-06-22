import { expect, test } from "@playwright/test";

const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://localhost:8000";

type AuthResponse = {
  access_token: string;
  user: { id: string };
};

type GenreList = { items: { id: string; name: string }[] };
type ProviderList = { items: { id: string; name: string }[] };
type TitleList = { items: { id: string; title: string }[] };

async function registerAndOnboard(request: import("@playwright/test").APIRequestContext) {
  const email = `e2e-${Date.now()}@example.com`;
  const password = "password123";

  const register = await request.post(`${API_URL}/auth/register`, {
    data: { email, password, display_name: "E2E User" },
  });
  expect(register.ok()).toBeTruthy();
  const auth = (await register.json()) as AuthResponse;
  const headers = { Authorization: `Bearer ${auth.access_token}` };

  const genresResponse = await request.get(`${API_URL}/catalog/genres`, { headers });
  const providersResponse = await request.get(`${API_URL}/catalog/providers`, { headers });

  if (genresResponse.ok() && providersResponse.ok()) {
    const genres = (await genresResponse.json()) as GenreList;
    const providers = (await providersResponse.json()) as ProviderList;

    if (genres.items.length > 0 && providers.items.length > 0) {
      await request.put(`${API_URL}/users/me/preferences`, {
        headers,
        data: {
          genre_ids: [genres.items[0].id],
          streaming_provider_ids: [providers.items[0].id],
        },
      });
    }
  }

  return { email, password, token: auth.access_token, headers };
}

test("login → home → detail → like", async ({ page, request }) => {
  const { email, password, headers } = await registerAndOnboard(request);

  await page.goto("/login");
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByRole("heading", { name: "Discover what to watch" })).toBeVisible({
    timeout: 20_000,
  });

  const trendingResponse = await request.get(`${API_URL}/catalog/trending?limit=1`, { headers });
  if (!trendingResponse.ok()) {
    test.skip(true, "Catalog API unavailable — run make init first");
  }

  const trending = (await trendingResponse.json()) as TitleList;
  if (trending.items.length === 0) {
    test.skip(true, "No titles in catalog — run make sync first");
  }

  const titleId = trending.items[0].id;
  await page.goto(`/titles/${titleId}`);

  await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 15_000 });
  await page.getByRole("button", { name: "Like" }).click();
  await expect(page.getByRole("button", { name: "Like" })).toHaveClass(/streamwise-accent/, {
    timeout: 10_000,
  });
});
