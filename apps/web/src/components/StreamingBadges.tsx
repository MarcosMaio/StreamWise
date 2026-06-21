import type { StreamingProviderBadge } from "@/lib/catalog";

type StreamingBadgesProps = {
  providers: StreamingProviderBadge[];
};

export function StreamingBadges({ providers }: StreamingBadgesProps) {
  const flatrateProviders = providers.filter(
    (provider) => provider.availability_type === "flatrate",
  );

  if (flatrateProviders.length === 0) {
    return (
      <div className="rounded-lg border border-white/10 bg-streamwise-surface px-4 py-3">
        <p className="text-sm font-medium">Where to watch in Brazil</p>
        <p className="mt-1 text-sm text-streamwise-muted">
          Not currently available on subscription streaming services in Brazil. Try checking
          rental or purchase options on your preferred platform, or check back after the next
          catalog sync.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium">Watch on subscription (Brazil)</p>
      <div className="flex flex-wrap gap-3">
        {flatrateProviders.map((provider) => (
          <div
            key={provider.id}
            className="flex items-center gap-2 rounded-lg border border-white/10 bg-streamwise-surface px-3 py-2"
          >
            {provider.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={provider.logo_url}
                alt={provider.name}
                className="h-8 w-8 rounded-md object-cover"
              />
            ) : (
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-streamwise-accent/20 text-xs font-semibold text-streamwise-accent">
                {provider.name.slice(0, 1)}
              </span>
            )}
            <span className="text-sm font-medium">{provider.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
