import Link from "next/link";

import type { TitleSummary } from "@/lib/catalog";

type TitleCardProps = {
  title: TitleSummary;
  href?: string;
};

export function TitleCard({ title, href }: TitleCardProps) {
  const typeLabel = title.type === "series" ? "Series" : "Movie";

  const card = (
    <article className="group overflow-hidden rounded-xl border border-white/10 bg-streamwise-surface transition hover:border-streamwise-accent/40">
      <div className="relative aspect-[2/3] bg-black/40">
        {title.poster_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={title.poster_url}
            alt={title.title}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center px-4 text-center text-sm text-streamwise-muted">
            No poster
          </div>
        )}
        <span className="absolute left-2 top-2 rounded-md bg-black/70 px-2 py-0.5 text-xs font-medium uppercase tracking-wide">
          {typeLabel}
        </span>
      </div>
      <div className="space-y-2 p-3">
        <h3 className="line-clamp-2 font-semibold leading-snug">{title.title}</h3>
        {title.genres.length > 0 ? (
          <p className="line-clamp-1 text-xs text-streamwise-muted">{title.genres.join(" · ")}</p>
        ) : null}
        {title.streaming_providers.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {title.streaming_providers.slice(0, 3).map((provider) => (
              <span
                key={provider.id}
                className="rounded-full bg-streamwise-accent/20 px-2 py-0.5 text-xs text-streamwise-accent"
              >
                {provider.name}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </article>
  );

  if (href) {
    return (
      <Link href={href} className="block">
        {card}
      </Link>
    );
  }

  return card;
}
