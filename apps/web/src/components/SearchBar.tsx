"use client";

import { FormEvent, useEffect, useState } from "react";

const EXAMPLE_QUERIES = [
  "Short funny series",
  "Intense thriller movie",
  "Cozy romance",
  "Family animation",
];

type SearchBarProps = {
  placeholder?: string;
  initialQuery?: string;
  onSearch: (query: string) => void;
  showExamples?: boolean;
};

export function SearchBar({
  placeholder = "Search titles…",
  initialQuery = "",
  onSearch,
  showExamples = true,
}: SearchBarProps) {
  const [query, setQuery] = useState(initialQuery);

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    onSearch(trimmed);
  }

  return (
    <div className="space-y-3">
      <form className="flex w-full max-w-md gap-2" onSubmit={handleSubmit}>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={placeholder}
          className="flex-1 rounded-lg border border-white/10 bg-streamwise-bg px-3 py-2 text-sm outline-none focus:border-streamwise-accent"
        />
        <button
          type="submit"
          className="rounded-lg bg-streamwise-accent px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
        >
          Search
        </button>
      </form>

      {showExamples ? (
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_QUERIES.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => {
                setQuery(example);
                onSearch(example);
              }}
              className="rounded-full border border-white/10 px-3 py-1 text-xs text-streamwise-muted transition hover:border-streamwise-accent/40 hover:text-white"
            >
              {example}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
