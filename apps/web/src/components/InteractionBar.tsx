"use client";

import { useState } from "react";

import { ApiError } from "@/lib/api-client";
import type { TitleSummary } from "@/lib/catalog";
import { recordInteraction, type EventType } from "@/lib/interactions";

type InteractionBarProps = {
  titleId: string;
  onTitleUpdated: (title: TitleSummary) => void;
};

type ActiveEvents = Partial<Record<EventType, boolean>>;

const ACTION_BUTTONS: { eventType: EventType; label: string }[] = [
  { eventType: "like", label: "Like" },
  { eventType: "dislike", label: "Dislike" },
  { eventType: "watchlist", label: "Watchlist" },
  { eventType: "watched", label: "Watched" },
];

export function InteractionBar({ titleId, onTitleUpdated }: InteractionBarProps) {
  const [active, setActive] = useState<ActiveEvents>({});
  const [selectedRating, setSelectedRating] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<EventType | "rating" | null>(null);

  async function handleAction(eventType: EventType) {
    setError(null);
    setLoading(eventType);

    try {
      const response = await recordInteraction(titleId, eventType);
      onTitleUpdated(response.title);

      if (eventType === "like") {
        setActive((current) => ({ ...current, like: true, dislike: false }));
      } else if (eventType === "dislike") {
        setActive((current) => ({ ...current, dislike: true, like: false }));
      } else {
        setActive((current) => ({ ...current, [eventType]: true }));
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setError("Unable to record this interaction.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(null);
    }
  }

  async function handleRate(rating: number) {
    setError(null);
    setLoading("rating");

    try {
      const response = await recordInteraction(titleId, "rating", rating);
      onTitleUpdated(response.title);
      setSelectedRating(rating);
    } catch {
      setError("Unable to save your rating.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <section className="space-y-4 rounded-xl border border-white/10 bg-streamwise-surface p-4">
      <h2 className="text-lg font-semibold">Your reaction</h2>

      <div className="flex flex-wrap gap-2">
        {ACTION_BUTTONS.map(({ eventType, label }) => {
          const isActive = active[eventType];
          const isLoading = loading === eventType;

          return (
            <button
              key={eventType}
              type="button"
              disabled={loading !== null}
              onClick={() => handleAction(eventType)}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition disabled:opacity-50 ${
                isActive
                  ? "bg-streamwise-accent text-white"
                  : "border border-white/10 bg-streamwise-bg text-streamwise-muted hover:border-streamwise-accent/40 hover:text-white"
              }`}
            >
              {isLoading ? "Saving…" : label}
            </button>
          );
        })}
      </div>

      <div className="space-y-2">
        <p className="text-sm text-streamwise-muted">Rate this title</p>
        <div className="flex flex-wrap gap-2">
          {[1, 2, 3, 4, 5].map((rating) => (
            <button
              key={rating}
              type="button"
              disabled={loading !== null}
              onClick={() => handleRate(rating)}
              className={`h-10 w-10 rounded-lg text-sm font-semibold transition disabled:opacity-50 ${
                selectedRating === rating
                  ? "bg-streamwise-accent text-white"
                  : "border border-white/10 bg-streamwise-bg text-streamwise-muted hover:border-streamwise-accent/40 hover:text-white"
              }`}
            >
              {rating}
            </button>
          ))}
        </div>
      </div>

      {error ? <p className="text-sm text-red-400">{error}</p> : null}
    </section>
  );
}
