"use client";

import Link from "next/link";
import { useState } from "react";

import { importWatchlistCsv, type ImportWatchlistResult } from "@/lib/profile";

export default function ImportWatchlistPage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportWatchlistResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!file) {
      setError("Choose a CSV file first.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await importWatchlistCsv(file);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <section className="space-y-3">
        <Link href="/profile" className="text-sm text-streamwise-accent hover:underline">
          Back to profile
        </Link>
        <h1 className="text-3xl font-bold">Import watchlist</h1>
        <p className="text-sm text-streamwise-muted">
          Upload a CSV with a <code className="text-white">tmdb_id</code> column. Each row is added
          to your watchlist when the title exists in StreamWise.
        </p>
      </section>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl border border-white/10 bg-streamwise-surface p-6"
      >
        <label className="block space-y-2 text-sm">
          <span className="font-medium">CSV file</span>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="block w-full text-sm text-streamwise-muted file:mr-4 file:rounded-md file:border-0 file:bg-streamwise-accent/20 file:px-4 file:py-2 file:text-sm file:font-medium file:text-streamwise-accent"
          />
        </label>

        <button
          type="submit"
          disabled={loading || !file}
          className="rounded-lg bg-streamwise-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-streamwise-accent/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Importing…" : "Import watchlist"}
        </button>
      </form>

      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      {result ? (
        <div className="space-y-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm">
          <p>
            Imported <strong>{result.imported}</strong> titles. Skipped{" "}
            <strong>{result.skipped}</strong>.
          </p>
          {result.missing_tmdb_ids.length > 0 ? (
            <p className="text-streamwise-muted">
              Missing from catalog (first 20): {result.missing_tmdb_ids.join(", ")}
            </p>
          ) : null}
        </div>
      ) : null}

      <section className="space-y-2 rounded-xl border border-white/10 bg-streamwise-surface p-6 text-sm text-streamwise-muted">
        <h2 className="text-base font-semibold text-white">Trakt (coming soon)</h2>
        <p>
          Trakt OAuth is available as an optional stub when{" "}
          <code className="text-white">TRAKT_CLIENT_ID</code> is configured. Use CSV import for
          now.
        </p>
      </section>
    </div>
  );
}
