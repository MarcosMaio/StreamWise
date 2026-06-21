import Link from "next/link";
import type { Metadata } from "next";

import { HeaderSearch } from "@/components/HeaderSearch";
import "./globals.css";

export const metadata: Metadata = {
  title: "StreamWise",
  description: "Discover movies and series tailored to your taste and streaming platforms.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-white/10 bg-streamwise-surface">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-4">
            <Link href="/" className="text-xl font-semibold tracking-tight text-streamwise-accent">
              StreamWise
            </Link>
            <HeaderSearch />
            <nav className="flex items-center gap-4 text-sm">
              <Link href="/explore" className="text-streamwise-muted hover:text-white">
                Explore
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
