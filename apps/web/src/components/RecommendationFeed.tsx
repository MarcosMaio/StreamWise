"use client";

import { TitleCard } from "@/components/TitleCard";
import type { RecommendationListResponse } from "@/lib/recommendations";

type RecommendationFeedProps = {
  data: RecommendationListResponse | null;
  loading?: boolean;
  error?: string | null;
};

export function RecommendationFeed({ data, loading, error }: RecommendationFeedProps) {
  if (loading) {
    return (
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">For you</h2>
        <p className="text-sm text-streamwise-muted">Personalizing your feed…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">For you</h2>
        <p className="text-sm text-red-400">{error}</p>
      </section>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">For you</h2>
        <p className="text-sm text-streamwise-muted">
          Like a few titles to unlock personalized recommendations.
        </p>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-semibold">For you</h2>
        {data.fallback_used ? (
          <p className="text-xs text-amber-200">
            Showing trending picks while the ranker warms up.
          </p>
        ) : null}
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {data.items.map((item) => (
          <TitleCard key={item.id} title={item} href={`/titles/${item.id}`} />
        ))}
      </div>
    </section>
  );
}
