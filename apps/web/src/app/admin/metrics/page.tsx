"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchRecommendationMetrics } from "@/lib/admin";

type BaselineMetrics = {
  precision_at_k?: number;
  recall_at_k?: number;
  ndcg_at_k?: number;
  coverage?: number;
  genre_diversity_at_k?: number;
};

function MetricBar({ label, value, max }: { label: string; value: number; max: number }) {
  const width = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span>{label}</span>
        <span className="text-streamwise-muted">{value.toFixed(4)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div className="h-full rounded-full bg-streamwise-accent" style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

export default function AdminMetricsPage() {
  const [adminToken, setAdminToken] = useState("");
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null);
  const [modelVersion, setModelVersion] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const envToken = process.env.NEXT_PUBLIC_ADMIN_API_KEY ?? "";
    if (envToken) {
      setAdminToken(envToken);
    }
  }, []);

  async function loadMetrics() {
    setError(null);
    try {
      const response = await fetchRecommendationMetrics(adminToken);
      setModelVersion(response.model_version);
      setMetrics(response.metrics);
    } catch {
      setError("Unable to load metrics. Check your admin token.");
    }
  }

  const offlineEval = (metrics?.offline_eval ?? metrics) as
    | { baselines?: Record<string, BaselineMetrics> }
    | undefined;
  const baselines = offlineEval?.baselines ?? {};

  return (
    <div className="space-y-8">
      <section className="space-y-2">
        <Link href="/" className="text-sm text-streamwise-accent hover:underline">
          Back to home
        </Link>
        <h1 className="text-3xl font-bold">Recommendation metrics</h1>
        <p className="text-streamwise-muted">Internal ML quality dashboard (dev/admin).</p>
      </section>

      <section className="flex flex-wrap items-end gap-3">
        <label className="space-y-1 text-sm">
          <span className="text-streamwise-muted">Admin token</span>
          <input
            type="password"
            value={adminToken}
            onChange={(event) => setAdminToken(event.target.value)}
            className="block w-64 rounded-lg border border-white/10 bg-streamwise-bg px-3 py-2"
          />
        </label>
        <button
          type="button"
          onClick={loadMetrics}
          className="rounded-lg bg-streamwise-accent px-4 py-2 text-sm font-medium text-white"
        >
          Load metrics
        </button>
      </section>

      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      {modelVersion ? (
        <p className="text-sm text-streamwise-muted">Active model: {modelVersion}</p>
      ) : null}

      {Object.keys(baselines).length > 0 ? (
        <div className="grid gap-6 md:grid-cols-2">
          {Object.entries(baselines).map(([name, baseline]) => {
            if ("skipped" in baseline && baseline.skipped) {
              return (
                <div key={name} className="rounded-xl border border-white/10 bg-streamwise-surface p-4">
                  <h2 className="mb-2 font-semibold capitalize">{name.replace("_", " ")}</h2>
                  <p className="text-sm text-streamwise-muted">Skipped</p>
                </div>
              );
            }

            const maxNdgc = Math.max(
              ...Object.values(baselines).map((item) => item.ndcg_at_k ?? 0),
              0.0001,
            );

            return (
              <div key={name} className="space-y-3 rounded-xl border border-white/10 bg-streamwise-surface p-4">
                <h2 className="font-semibold capitalize">{name.replace("_", " ")}</h2>
                <MetricBar label="Precision@10" value={baseline.precision_at_k ?? 0} max={1} />
                <MetricBar label="Recall@10" value={baseline.recall_at_k ?? 0} max={1} />
                <MetricBar label="NDCG@10" value={baseline.ndcg_at_k ?? 0} max={maxNdgc} />
                <MetricBar label="Coverage" value={baseline.coverage ?? 0} max={1} />
                <MetricBar
                  label="Genre diversity@10"
                  value={baseline.genre_diversity_at_k ?? 0}
                  max={1}
                />
              </div>
            );
          })}
        </div>
      ) : metrics ? (
        <pre className="overflow-auto rounded-xl border border-white/10 bg-black/30 p-4 text-xs">
          {JSON.stringify(metrics, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}
