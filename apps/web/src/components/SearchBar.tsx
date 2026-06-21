"use client";

import { FormEvent, useEffect, useState } from "react";

type SearchBarProps = {
  placeholder?: string;
  initialQuery?: string;
  onSearch: (query: string) => void;
};

export function SearchBar({
  placeholder = "Search titles…",
  initialQuery = "",
  onSearch,
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
  );
}
