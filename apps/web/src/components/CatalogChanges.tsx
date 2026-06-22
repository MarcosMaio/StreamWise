"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchCatalogChanges, type CatalogChangeItem } from "@/lib/catalog";

function formatChange(item: CatalogChangeItem): string {
  const verb = item.change_type === "enter" ? "joined" : "left";
  return `${item.title_name} ${verb} ${item.provider_name}`;
}

export function CatalogChanges() {
  const [items, setItems] = useState<CatalogChangeItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCatalogChanges(8)
      .then((response) => setItems(response.items))
      .catch(() => setError("Unable to load catalog changes."));
  }, []);

  if (error) {
    return null;
  }

  if (items.length === 0) {
    return null;
  }

  return (
    <section className="space-y-3 rounded-xl border border-white/10 bg-streamwise-surface p-6">
      <div className="space-y-1">
        <h2 className="text-xl font-semibold">Streaming catalog updates</h2>
        <p className="text-sm text-streamwise-muted">
          Recent enter/leave events on subscription platforms in Brazil.
        </p>
      </div>
      <ul className="space-y-2 text-sm">
        {items.map((item) => (
          <li key={item.id} className="flex flex-wrap items-center gap-2">
            <span
              className={
                item.change_type === "enter"
                  ? "rounded-full bg-emerald-500/20 px-2 py-0.5 text-xs text-emerald-200"
                  : "rounded-full bg-rose-500/20 px-2 py-0.5 text-xs text-rose-200"
              }
            >
              {item.change_type === "enter" ? "New" : "Leaving"}
            </span>
            <Link
              href={`/titles/${item.title_id}`}
              className="text-streamwise-accent hover:underline"
            >
              {formatChange(item)}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
