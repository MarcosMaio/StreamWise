"use client";

import { useRouter } from "next/navigation";

import { SearchBar } from "@/components/SearchBar";

export function HeaderSearch() {
  const router = useRouter();

  function handleSearch(query: string) {
    router.push(`/explore?q=${encodeURIComponent(query)}`);
  }

  return <SearchBar placeholder="Search movies and series…" onSearch={handleSearch} />;
}
