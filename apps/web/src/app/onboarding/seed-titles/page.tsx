"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { TitleCard } from "@/components/TitleCard";
import { ApiError } from "@/lib/api-client";
import { fetchTrending, type TitleSummary } from "@/lib/catalog";
import {
  clearOnboardingDraft,
  loadOnboardingDraft,
  savePreferences,
  toggleSelection,
  type OnboardingDraft,
} from "@/lib/onboarding";

export default function SeedTitlesPage() {
  const router = useRouter();
  const [draft, setDraft] = useState<OnboardingDraft | null>(null);
  const [titles, setTitles] = useState<TitleSummary[]>([]);
  const [selectedTitles, setSelectedTitles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const savedDraft = loadOnboardingDraft();
    if (!savedDraft) {
      router.replace("/onboarding");
      return;
    }
    setDraft(savedDraft);

    fetchTrending("all", 24)
      .then((response) => setTitles(response.items))
      .catch(() => setError("Unable to load titles for seed selection."))
      .finally(() => setLoading(false));
  }, [router]);

  async function finishOnboarding() {
    if (!draft) return;

    setSubmitting(true);
    setError(null);

    try {
      await savePreferences({
        genre_ids: draft.genre_ids,
        streaming_provider_ids: draft.streaming_provider_ids,
        seed_like_title_ids: selectedTitles,
      });
      clearOnboardingDraft();
      router.push("/");
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setError("Please review your selections and try again.");
      } else {
        setError("Unable to save preferences. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (!draft || loading) {
    return <p className="text-sm text-streamwise-muted">Loading titles…</p>;
  }

  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <p className="text-sm font-medium uppercase tracking-wide text-streamwise-accent">
          Step 2 of 2
        </p>
        <h1 className="text-3xl font-bold">Anything you already love?</h1>
        <p className="max-w-2xl text-streamwise-muted">
          Optional: mark a few titles you enjoy so StreamWise can personalize your feed faster.
        </p>
      </section>

      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      {titles.length === 0 ? (
        <p className="text-sm text-streamwise-muted">
          No catalog titles yet. You can finish onboarding and sync the catalog later.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {titles.map((title) => {
            const selected = selectedTitles.includes(title.id);
            return (
              <button
                key={title.id}
                type="button"
                onClick={() =>
                  setSelectedTitles((current) => toggleSelection(current, title.id))
                }
                className={`rounded-xl text-left transition ${
                  selected ? "ring-2 ring-streamwise-accent ring-offset-2 ring-offset-streamwise-bg" : ""
                }`}
              >
                <TitleCard title={title} />
              </button>
            );
          })}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-4">
        <button
          type="button"
          disabled={submitting}
          onClick={finishOnboarding}
          className="rounded-lg bg-streamwise-accent px-6 py-3 font-medium text-white transition hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? "Saving…" : selectedTitles.length > 0 ? "Finish onboarding" : "Skip for now"}
        </button>
        <Link href="/onboarding" className="text-sm text-streamwise-muted hover:text-white">
          Back to genres and services
        </Link>
      </div>
    </div>
  );
}
