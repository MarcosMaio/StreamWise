"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  fetchGenres,
  fetchProviders,
  saveOnboardingDraft,
  toggleSelection,
  type GenreOption,
  type ProviderOption,
} from "@/lib/onboarding";

export default function OnboardingPage() {
  const router = useRouter();
  const [genres, setGenres] = useState<GenreOption[]>([]);
  const [providers, setProviders] = useState<ProviderOption[]>([]);
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchGenres(), fetchProviders()])
      .then(([genreItems, providerItems]) => {
        setGenres(genreItems);
        setProviders(providerItems);
      })
      .catch(() => setError("Unable to load onboarding options."))
      .finally(() => setLoading(false));
  }, []);

  function handleContinue() {
    if (selectedGenres.length === 0 || selectedProviders.length === 0) {
      setError("Select at least one genre and one streaming service to continue.");
      return;
    }

    saveOnboardingDraft({
      genre_ids: selectedGenres,
      streaming_provider_ids: selectedProviders,
    });
    router.push("/onboarding/seed-titles");
  }

  if (loading) {
    return <p className="text-sm text-streamwise-muted">Loading onboarding…</p>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <section className="space-y-2">
        <p className="text-sm font-medium uppercase tracking-wide text-streamwise-accent">
          Step 1 of 2
        </p>
        <h1 className="text-3xl font-bold">Tell us what you like</h1>
        <p className="text-streamwise-muted">
          Pick your favorite genres and the streaming services you use in Brazil.
        </p>
      </section>

      <section className="space-y-4 rounded-xl border border-white/10 bg-streamwise-surface p-6">
        <div className="space-y-2">
          <h2 className="text-lg font-semibold">Favorite genres</h2>
          <p className="text-sm text-streamwise-muted">Choose all that apply.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {genres.map((genre) => {
            const selected = selectedGenres.includes(genre.id);
            return (
              <button
                key={genre.id}
                type="button"
                onClick={() => setSelectedGenres((current) => toggleSelection(current, genre.id))}
                className={`rounded-full px-4 py-2 text-sm transition ${
                  selected
                    ? "bg-streamwise-accent text-white"
                    : "border border-white/10 bg-streamwise-bg text-streamwise-muted hover:border-streamwise-accent/40"
                }`}
              >
                {genre.name}
              </button>
            );
          })}
        </div>
      </section>

      <section className="space-y-4 rounded-xl border border-white/10 bg-streamwise-surface p-6">
        <div className="space-y-2">
          <h2 className="text-lg font-semibold">Streaming services</h2>
          <p className="text-sm text-streamwise-muted">Where do you watch today?</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {providers.map((provider) => {
            const selected = selectedProviders.includes(provider.id);
            return (
              <button
                key={provider.id}
                type="button"
                onClick={() =>
                  setSelectedProviders((current) => toggleSelection(current, provider.id))
                }
                className={`rounded-full px-4 py-2 text-sm transition ${
                  selected
                    ? "bg-streamwise-accent text-white"
                    : "border border-white/10 bg-streamwise-bg text-streamwise-muted hover:border-streamwise-accent/40"
                }`}
              >
                {provider.name}
              </button>
            );
          })}
        </div>
      </section>

      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      <button
        type="button"
        onClick={handleContinue}
        className="rounded-lg bg-streamwise-accent px-6 py-3 font-medium text-white transition hover:opacity-90"
      >
        Continue
      </button>
    </div>
  );
}
