"use client";

import { useEffect, useRef } from "react";

import type { ProviderOption } from "@/lib/onboarding";

type ProviderFilterProps = {
  providers: ProviderOption[];
  selectedIds: string[];
  defaultSelectedIds?: string[];
  onChange: (ids: string[]) => void;
  label?: string;
};

export function ProviderFilter({
  providers,
  selectedIds,
  defaultSelectedIds = [],
  onChange,
  label = "Streaming services",
}: ProviderFilterProps) {
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current || selectedIds.length > 0 || defaultSelectedIds.length === 0) {
      return;
    }
    initialized.current = true;
    onChange(defaultSelectedIds);
  }, [defaultSelectedIds, onChange, selectedIds.length]);

  function toggleProvider(id: string) {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((item) => item !== id));
      return;
    }
    onChange([...selectedIds, id]);
  }

  if (providers.length === 0) {
    return null;
  }

  return (
    <section className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium">{label}</p>
        {selectedIds.length > 0 ? (
          <button
            type="button"
            onClick={() => onChange([])}
            className="text-xs text-streamwise-muted hover:text-white"
          >
            Clear filters
          </button>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-2">
        {providers.map((provider) => {
          const selected = selectedIds.includes(provider.id);
          return (
            <button
              key={provider.id}
              type="button"
              onClick={() => toggleProvider(provider.id)}
              className={`rounded-full px-4 py-2 text-sm transition ${
                selected
                  ? "bg-streamwise-accent text-white"
                  : "border border-white/10 bg-streamwise-surface text-streamwise-muted hover:border-streamwise-accent/40"
              }`}
            >
              {provider.name}
            </button>
          );
        })}
      </div>
    </section>
  );
}
