"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { TitleCard } from "@/components/TitleCard";
import { fetchContinueWatching, type ContinueWatchingResponse } from "@/lib/profile";

export default function ContinueWatchingPage() {
  const [data, setData] = useState<ContinueWatchingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchContinueWatching()
      .then(setData)
      .catch(() => setError("Unable to load continue watching list."));
  }, []);

  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <Link href="/" className="text-sm text-streamwise-accent hover:underline">
          Back to home
        </Link>
        <h1 className="text-3xl font-bold">Continue watching</h1>
        <p className="text-streamwise-muted">Pick up series where you left off.</p>
      </section>

      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      {!data ? (
        <p className="text-sm text-streamwise-muted">Loading…</p>
      ) : data.items.length === 0 ? (
        <p className="text-sm text-streamwise-muted">
          No series in progress yet. Open a series detail page to save your season and episode.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {data.items.map((item) => (
            <TitleCard
              key={item.id}
              title={item}
              href={`/titles/${item.id}`}
              progress={{ season: item.season, episode: item.episode }}
            />
          ))}
        </div>
      )}
    </div>
  );
}
