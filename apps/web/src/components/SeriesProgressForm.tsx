"use client";

import { FormEvent, useState } from "react";

import { updateSeriesProgress } from "@/lib/interactions";

type SeriesProgressFormProps = {
  titleId: string;
};

export function SeriesProgressForm({ titleId }: SeriesProgressFormProps) {
  const [season, setSeason] = useState(1);
  const [episode, setEpisode] = useState(1);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      await updateSeriesProgress(titleId, season, episode);
      setMessage(`Saved progress at S${season} E${episode}.`);
    } catch {
      setError("Unable to save series progress.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-3 rounded-xl border border-white/10 bg-streamwise-surface p-4">
      <h2 className="text-lg font-semibold">Continue watching</h2>
      <p className="text-sm text-streamwise-muted">Save where you left off in this series.</p>
      <form className="flex flex-wrap items-end gap-3" onSubmit={handleSubmit}>
        <label className="space-y-1 text-sm">
          <span className="text-streamwise-muted">Season</span>
          <input
            type="number"
            min={1}
            value={season}
            onChange={(event) => setSeason(Number(event.target.value))}
            className="block w-24 rounded-lg border border-white/10 bg-streamwise-bg px-3 py-2"
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="text-streamwise-muted">Episode</span>
          <input
            type="number"
            min={1}
            value={episode}
            onChange={(event) => setEpisode(Number(event.target.value))}
            className="block w-24 rounded-lg border border-white/10 bg-streamwise-bg px-3 py-2"
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-streamwise-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {loading ? "Saving…" : "Save progress"}
        </button>
      </form>
      {message ? <p className="text-sm text-green-400">{message}</p> : null}
      {error ? <p className="text-sm text-red-400">{error}</p> : null}
    </section>
  );
}
