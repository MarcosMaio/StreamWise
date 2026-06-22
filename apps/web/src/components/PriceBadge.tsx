import type { StreamingProviderBadge } from "@/lib/catalog";

type PriceBadgeProps = {
  flatrateProviders: StreamingProviderBadge[];
  rentProviders: StreamingProviderBadge[];
  buyProviders: StreamingProviderBadge[];
};

export function PriceBadge({
  flatrateProviders,
  rentProviders,
  buyProviders,
}: PriceBadgeProps) {
  const hasSubscription = flatrateProviders.length > 0;
  const hasRent = rentProviders.length > 0;
  const hasBuy = buyProviders.length > 0;

  if (hasSubscription) {
    return (
      <span className="inline-flex items-center rounded-md bg-emerald-500/20 px-2 py-0.5 text-xs font-medium text-emerald-200">
        Included with subscription
      </span>
    );
  }

  if (hasRent || hasBuy) {
    const labels: string[] = [];
    if (hasRent) labels.push("Rent");
    if (hasBuy) labels.push("Buy");
    return (
      <span className="inline-flex items-center rounded-md bg-sky-500/20 px-2 py-0.5 text-xs font-medium text-sky-200">
        {labels.join(" or ")} only
      </span>
    );
  }

  return (
    <span className="inline-flex items-center rounded-md bg-white/10 px-2 py-0.5 text-xs font-medium text-streamwise-muted">
      Availability unknown
    </span>
  );
}
