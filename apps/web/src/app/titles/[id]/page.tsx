"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { CommunityRating } from "@/components/CommunityRating";
import { InteractionBar } from "@/components/InteractionBar";
import { PriceBadge } from "@/components/PriceBadge";
import { SeriesProgressForm } from "@/components/SeriesProgressForm";
import { StreamingBadges } from "@/components/StreamingBadges";
import { TitleCard } from "@/components/TitleCard";
import {
  fetchSimilarTitles,
  fetchTitleDetail,
  type TitleDetail,
  type TitleListResponse,
} from "@/lib/catalog";

function formatReleaseYear(releaseDate: string | null): string | null {
  if (!releaseDate) return null;
  const year = releaseDate.slice(0, 4);
  return year || null;
}

export default function TitleDetailPage() {
  const params = useParams<{ id: string }>();
  const [title, setTitle] = useState<TitleDetail | null>(null);
  const [similar, setSimilar] = useState<TitleListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!params.id) return;

    fetchTitleDetail(params.id)
      .then((detail) => {
        setTitle(detail);
        return fetchSimilarTitles(params.id);
      })
      .then(setSimilar)
      .catch(() => setError("Unable to load this title. It may have been removed."))
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) {
    return <p className="text-sm text-streamwise-muted">Loading title…</p>;
  }

  if (error || !title) {
    return (
      <div className="space-y-4">
        <Link href="/" className="text-sm text-streamwise-accent hover:underline">
          Back to home
        </Link>
        <p className="text-sm text-red-400">{error ?? "Title not found."}</p>
      </div>
    );
  }

  const releaseYear = formatReleaseYear(title.release_date);
  const typeLabel = title.type === "series" ? "Series" : "Movie";

  return (
    <div className="space-y-8">
      <Link href="/" className="inline-block text-sm text-streamwise-accent hover:underline">
        Back to home
      </Link>

      {title.availability_note ? (
        <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-200">
          {title.availability_note}
        </p>
      ) : null}

      <div className="grid gap-8 lg:grid-cols-[280px_1fr]">
        <div className="overflow-hidden rounded-xl border border-white/10 bg-streamwise-surface">
          <div className="aspect-[2/3] bg-black/40">
            {title.poster_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={title.poster_url}
                alt={title.title}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center px-4 text-center text-sm text-streamwise-muted">
                No poster available
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-md bg-streamwise-accent/20 px-2 py-0.5 text-xs font-medium uppercase tracking-wide text-streamwise-accent">
                {typeLabel}
              </span>
              {title.is_trending ? (
                <span className="rounded-md bg-amber-500/20 px-2 py-0.5 text-xs font-medium text-amber-200">
                  Trending
                </span>
              ) : null}
              {releaseYear ? (
                <span className="text-sm text-streamwise-muted">{releaseYear}</span>
              ) : null}
            </div>
            <h1 className="text-3xl font-bold leading-tight">{title.title}</h1>
            <div className="flex flex-wrap items-center gap-2">
              <PriceBadge
                flatrateProviders={title.streaming_providers.filter(
                  (provider) => provider.availability_type === "flatrate",
                )}
                rentProviders={title.rent_providers ?? []}
                buyProviders={title.buy_providers ?? []}
              />
              {title.certification ? (
                <span className="text-xs text-streamwise-muted">Rating: {title.certification}</span>
              ) : null}
            </div>
            {title.genres.length > 0 ? (
              <p className="text-sm text-streamwise-muted">{title.genres.join(" · ")}</p>
            ) : null}
          </div>

          <CommunityRating
            averageRating={title.streamwise_avg_rating}
            likeCount={title.like_count}
          />

          <InteractionBar
            titleId={title.id}
            onTitleUpdated={(updated) =>
              setTitle((current) => (current ? { ...current, ...updated } : current))
            }
          />

          {title.type === "series" ? (
            <SeriesProgressForm titleId={title.id} />
          ) : null}

          <section className="space-y-2">
            <h2 className="text-lg font-semibold">Synopsis</h2>
            <p className="text-streamwise-muted">
              {title.overview?.trim() || "No synopsis available for this title yet."}
            </p>
          </section>

          <StreamingBadges providers={title.streaming_providers} />

          {(title.rent_providers?.length ?? 0) > 0 || (title.buy_providers?.length ?? 0) > 0 ? (
            <section className="space-y-2">
              <h2 className="text-lg font-semibold">Rent or buy</h2>
              <div className="flex flex-wrap gap-2">
                {[...(title.rent_providers ?? []), ...(title.buy_providers ?? [])].map(
                  (provider) => (
                    <span
                      key={`${provider.id}-${provider.availability_type}`}
                      className="rounded-lg border border-white/10 bg-streamwise-surface px-3 py-1 text-sm"
                    >
                      {provider.name} ({provider.availability_type})
                    </span>
                  ),
                )}
              </div>
            </section>
          ) : null}
        </div>
      </div>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">More like this</h2>
        {similar === null ? (
          <p className="text-sm text-streamwise-muted">Loading similar titles…</p>
        ) : similar.items.length === 0 ? (
          <p className="text-sm text-streamwise-muted">
            No similar titles yet. Run the embedding pipeline after syncing the catalog.
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {similar.items.map((item) => (
              <TitleCard key={item.id} title={item} href={`/titles/${item.id}`} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
