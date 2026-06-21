"use client";

import { useCallback, useEffect, useState } from "react";

import { ProviderFilter } from "@/components/ProviderFilter";
import { RecommendationFeed } from "@/components/RecommendationFeed";
import { TitleCard } from "@/components/TitleCard";
import { fetchCurrentUser, logout, type AuthUser } from "@/lib/auth";
import { fetchNewReleases, fetchTrending, type TitleListResponse } from "@/lib/catalog";
import { fetchProviders, type ProviderOption } from "@/lib/onboarding";
import { fetchForYouFeed, type RecommendationListResponse } from "@/lib/recommendations";

function TitleRow({ label, data }: { label: string; data: TitleListResponse | null }) {
  if (!data) {
    return (
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">{label}</h2>
        <p className="text-sm text-streamwise-muted">Loading…</p>
      </section>
    );
  }

  if (data.items.length === 0) {
    return (
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">{label}</h2>
        <p className="text-sm text-streamwise-muted">No titles match the selected platforms.</p>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold">{label}</h2>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {data.items.map((title) => (
          <TitleCard key={title.id} title={title} href={`/titles/${title.id}`} />
        ))}
      </div>
    </section>
  );
}

export default function HomePage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [providers, setProviders] = useState<ProviderOption[]>([]);
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [trending, setTrending] = useState<TitleListResponse | null>(null);
  const [newReleases, setNewReleases] = useState<TitleListResponse | null>(null);
  const [forYou, setForYou] = useState<RecommendationListResponse | null>(null);
  const [forYouError, setForYouError] = useState<string | null>(null);
  const [forYouLoading, setForYouLoading] = useState(true);
  const [staleNote, setStaleNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadFeeds = useCallback(
    async (providerIds: string[]) => {
      const filters = { providerIds };
      setForYouLoading(true);
      setForYouError(null);

      try {
        const [forYouData, trendingData, newData] = await Promise.all([
          fetchForYouFeed(20, providerIds),
          fetchTrending("all", 20, filters),
          fetchNewReleases(20, filters),
        ]);
        setForYou(forYouData);
        setTrending(trendingData);
        setNewReleases(newData);
        const note =
          trendingData.availability_note ||
          newData.availability_note ||
          (trendingData.stale_data || newData.stale_data
            ? "Catalog data may be outdated."
            : null);
        setStaleNote(note ?? null);
      } catch {
        setForYouError("Unable to load personalized recommendations.");
        setError("Unable to load catalog. Try signing in again.");
      } finally {
        setForYouLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    fetchCurrentUser()
      .then(setUser)
      .catch(() => setError("Unable to load your profile."));

    fetchProviders()
      .then(setProviders)
      .catch(() => setError("Unable to load streaming providers."));
  }, []);

  useEffect(() => {
    loadFeeds(selectedProviders);
  }, [loadFeeds, selectedProviders]);

  function handleLogout() {
    logout();
    window.location.href = "/login";
  }

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Discover what to watch</h1>
            <p className="mt-2 max-w-2xl text-streamwise-muted">
              Trending titles and new releases with Brazil streaming availability.
            </p>
          </div>
          {user ? (
            <div className="rounded-xl border border-white/10 bg-streamwise-surface px-4 py-3 text-sm">
              <p className="font-medium">{user.display_name}</p>
              <button
                type="button"
                onClick={handleLogout}
                className="mt-2 text-streamwise-muted hover:text-white"
              >
                Sign out
              </button>
            </div>
          ) : null}
        </div>

        <ProviderFilter
          providers={providers}
          selectedIds={selectedProviders}
          defaultSelectedIds={user?.streaming_provider_ids ?? []}
          onChange={setSelectedProviders}
        />

        {staleNote ? (
          <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-200">
            {staleNote}
          </p>
        ) : null}

        {error ? <p className="text-sm text-red-400">{error}</p> : null}
      </section>

      <RecommendationFeed data={forYou} loading={forYouLoading} error={forYouError} />

      <TitleRow label="Trending" data={trending} />
      <TitleRow label="New releases" data={newReleases} />
    </div>
  );
}
