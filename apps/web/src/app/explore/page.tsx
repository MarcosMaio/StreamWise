"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { ProviderFilter } from "@/components/ProviderFilter";
import { SearchBar } from "@/components/SearchBar";
import { TitleCard } from "@/components/TitleCard";
import {
  fetchTrending,
  searchCatalog,
  type CatalogFilters,
  type TitleListResponse,
} from "@/lib/catalog";
import { fetchGenres, fetchProviders, type GenreOption, type ProviderOption } from "@/lib/onboarding";

function ExploreContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") ?? "";

  const [providers, setProviders] = useState<ProviderOption[]>([]);
  const [genres, setGenres] = useState<GenreOption[]>([]);
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const [titleType, setTitleType] = useState<"all" | "movie" | "series">("all");
  const [results, setResults] = useState<TitleListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadResults = useCallback(async () => {
    setLoading(true);
    setError(null);
    const filters: CatalogFilters = {
      providerIds: selectedProviders,
      genreIds: selectedGenres,
    };

    try {
      if (searchQuery.trim()) {
        const data = await searchCatalog(searchQuery.trim(), 24, filters);
        setResults(data);
        return;
      }

      const data = await fetchTrending(titleType, 24, filters);
      setResults(data);
    } catch {
      setError("Unable to load explore results.");
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedGenres, selectedProviders, titleType]);

  useEffect(() => {
    Promise.all([fetchProviders(), fetchGenres()])
      .then(([providerItems, genreItems]) => {
        setProviders(providerItems);
        setGenres(genreItems);
      })
      .catch(() => setError("Unable to load filters."));
  }, []);

  useEffect(() => {
    setSearchQuery(initialQuery);
  }, [initialQuery]);

  useEffect(() => {
    loadResults();
  }, [loadResults]);

  function handleSearch(query: string) {
    router.push(`/explore?q=${encodeURIComponent(query)}`);
  }

  function toggleGenre(id: string) {
    setSelectedGenres((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  }

  return (
    <div className="space-y-8">
      <section className="space-y-4">
        <Link href="/" className="text-sm text-streamwise-accent hover:underline">
          Back to home
        </Link>
        <div className="space-y-2">
          <h1 className="text-3xl font-bold">Explore</h1>
          <p className="text-streamwise-muted">
            Search titles or filter trending catalog by genre, type, and streaming platform.
          </p>
        </div>
        <SearchBar
          initialQuery={searchQuery}
          placeholder="Try: short funny series"
          onSearch={handleSearch}
        />
      </section>

      <ProviderFilter
        providers={providers}
        selectedIds={selectedProviders}
        onChange={setSelectedProviders}
        label="Platforms"
      />

      {!searchQuery ? (
        <>
          <section className="space-y-2">
            <p className="text-sm font-medium">Genres</p>
            <div className="flex flex-wrap gap-2">
              {genres.map((genre) => {
                const selected = selectedGenres.includes(genre.id);
                return (
                  <button
                    key={genre.id}
                    type="button"
                    onClick={() => toggleGenre(genre.id)}
                    className={`rounded-full px-4 py-2 text-sm transition ${
                      selected
                        ? "bg-streamwise-accent text-white"
                        : "border border-white/10 bg-streamwise-surface text-streamwise-muted hover:border-streamwise-accent/40"
                    }`}
                  >
                    {genre.name}
                  </button>
                );
              })}
            </div>
          </section>

          <section className="space-y-2">
            <p className="text-sm font-medium">Type</p>
            <div className="flex flex-wrap gap-2">
              {(["all", "movie", "series"] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setTitleType(value)}
                  className={`rounded-full px-4 py-2 text-sm capitalize transition ${
                    titleType === value
                      ? "bg-streamwise-accent text-white"
                      : "border border-white/10 bg-streamwise-surface text-streamwise-muted hover:border-streamwise-accent/40"
                  }`}
                >
                  {value}
                </button>
              ))}
            </div>
          </section>
        </>
      ) : null}

      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">
          {searchQuery ? `Results for “${searchQuery}”` : "Trending results"}
        </h2>
        {loading ? (
          <p className="text-sm text-streamwise-muted">Loading titles…</p>
        ) : !results || results.items.length === 0 ? (
          <p className="text-sm text-streamwise-muted">No titles match these filters.</p>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {results.items.map((title) => (
              <TitleCard key={title.id} title={title} href={`/titles/${title.id}`} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default function ExplorePage() {
  return (
    <Suspense fallback={<p className="text-sm text-streamwise-muted">Loading explore…</p>}>
      <ExploreContent />
    </Suspense>
  );
}
