"use client";

import Link from "next/link";

import { TitleCard } from "@/components/TitleCard";
import { logBanditClick, type RecommendationListResponse } from "@/lib/recommendations";

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
          <div key={item.id} className="space-y-2">
            <Link
              href={`/titles/${item.id}`}
              onClick={() => {
                if (item.exploration) {
                  void logBanditClick(item.id, true).catch(() => undefined);
                }
              }}
            >
              <TitleCard title={item} />
            </Link>
            <div className="flex flex-wrap gap-1 px-1">
              {item.exploration ? (
                <span className="rounded-full bg-violet-500/20 px-2 py-0.5 text-[11px] text-violet-200">
                  Explore
                </span>
              ) : null}
              {item.reason_tags?.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-white/5 px-2 py-0.5 text-[11px] text-streamwise-muted"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
