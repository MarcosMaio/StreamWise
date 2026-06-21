"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AffinityChart } from "@/components/AffinityChart";
import { TitleCard } from "@/components/TitleCard";
import { logout, type AuthUser } from "@/lib/auth";
import type { TitleListResponse } from "@/lib/catalog";
import { fetchGenres, type GenreOption } from "@/lib/onboarding";
import {
  fetchStreamingAffinity,
  fetchUserLikes,
  fetchUserProfile,
  fetchUserWatchlist,
  type StreamingAffinityResponse,
} from "@/lib/profile";

function TitleGrid({ data, emptyMessage }: { data: TitleListResponse | null; emptyMessage: string }) {
  if (!data) {
    return <p className="text-sm text-streamwise-muted">Loading titles…</p>;
  }

  if (data.items.length === 0) {
    return <p className="text-sm text-streamwise-muted">{emptyMessage}</p>;
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {data.items.map((title) => (
        <TitleCard key={title.id} title={title} href={`/titles/${title.id}`} />
      ))}
    </div>
  );
}

export default function ProfilePage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [genres, setGenres] = useState<GenreOption[]>([]);
  const [likes, setLikes] = useState<TitleListResponse | null>(null);
  const [watchlist, setWatchlist] = useState<TitleListResponse | null>(null);
  const [affinity, setAffinity] = useState<StreamingAffinityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchUserProfile(),
      fetchGenres(),
      fetchUserLikes(),
      fetchUserWatchlist(),
      fetchStreamingAffinity(),
    ])
      .then(([profile, genreOptions, likesData, watchlistData, affinityData]) => {
        setUser(profile);
        setGenres(genreOptions);
        setLikes(likesData);
        setWatchlist(watchlistData);
        setAffinity(affinityData);
      })
      .catch(() => setError("Unable to load your profile."));
  }, []);

  const preferredGenres = genres.filter((genre) => user?.genre_ids.includes(genre.id));

  function handleLogout() {
    logout();
    window.location.href = "/login";
  }

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <Link href="/" className="text-sm text-streamwise-accent hover:underline">
          Back to home
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <h1 className="text-3xl font-bold">Your profile</h1>
            {user ? (
              <>
                <p className="text-lg font-medium">{user.display_name}</p>
                <p className="text-sm text-streamwise-muted">{user.email}</p>
              </>
            ) : (
              <p className="text-sm text-streamwise-muted">Loading profile…</p>
            )}
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-lg border border-white/10 px-4 py-2 text-sm text-streamwise-muted transition hover:border-white/20 hover:text-white"
          >
            Sign out
          </button>
        </div>
        {error ? <p className="text-sm text-red-400">{error}</p> : null}
      </section>

      <section className="space-y-3 rounded-xl border border-white/10 bg-streamwise-surface p-6">
        <h2 className="text-xl font-semibold">Genre preferences</h2>
        {preferredGenres.length === 0 ? (
          <p className="text-sm text-streamwise-muted">No genre preferences saved yet.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {preferredGenres.map((genre) => (
              <span
                key={genre.id}
                className="rounded-full bg-streamwise-accent/20 px-3 py-1 text-sm text-streamwise-accent"
              >
                {genre.name}
              </span>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3 rounded-xl border border-white/10 bg-streamwise-surface p-6">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold">Streaming affinity</h2>
          <p className="text-sm text-streamwise-muted">
            Inferred from titles you like and onboarding choices.
          </p>
        </div>
        <AffinityChart providers={affinity?.providers ?? []} />
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Likes</h2>
        <TitleGrid data={likes} emptyMessage="You have not liked any titles yet." />
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Watchlist</h2>
        <TitleGrid
          data={watchlist}
          emptyMessage="Your watchlist is empty. Add titles from a title detail page."
        />
      </section>
    </div>
  );
}
