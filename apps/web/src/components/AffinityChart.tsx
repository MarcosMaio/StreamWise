import type { StreamingAffinity } from "@/lib/profile";

type AffinityChartProps = {
  providers: StreamingAffinity[];
};

export function AffinityChart({ providers }: AffinityChartProps) {
  if (providers.length === 0) {
    return (
      <p className="text-sm text-streamwise-muted">
        Like titles to help StreamWise infer which streaming services you use most.
      </p>
    );
  }

  const maxScore = Math.max(...providers.map((item) => item.score), 0.01);

  return (
    <div className="space-y-3">
      {providers.map((provider) => {
        const widthPercent = Math.round((provider.score / maxScore) * 100);
        const percentLabel = `${Math.round(provider.score * 100)}%`;

        return (
          <div key={provider.provider_id} className="space-y-1">
            <div className="flex items-center justify-between gap-4 text-sm">
              <span className="font-medium">{provider.provider_name}</span>
              <span className="text-streamwise-muted">{percentLabel}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-streamwise-accent transition-all"
                style={{ width: `${widthPercent}%` }}
                role="progressbar"
                aria-valuenow={Math.round(provider.score * 100)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${provider.provider_name} affinity`}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
