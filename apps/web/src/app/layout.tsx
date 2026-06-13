import type { Metadata } from "next";
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
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
            <span className="text-xl font-semibold tracking-tight text-streamwise-accent">
              StreamWise
            </span>
            <span className="text-sm text-streamwise-muted">Discovery hub</span>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
