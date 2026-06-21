type CommunityRatingProps = {
  averageRating: number | null;
  likeCount: number;
};

export function CommunityRating({ averageRating, likeCount }: CommunityRatingProps) {
  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border border-white/10 bg-streamwise-surface px-4 py-3">
      <div>
        <p className="text-xs uppercase tracking-wide text-streamwise-muted">StreamWise rating</p>
        <p className="text-2xl font-semibold">
          {averageRating !== null ? averageRating.toFixed(1) : "—"}
        </p>
        <p className="text-xs text-streamwise-muted">
          {averageRating !== null ? "Average from user ratings" : "No ratings yet"}
        </p>
      </div>
      <div className="h-10 w-px bg-white/10" aria-hidden />
      <div>
        <p className="text-xs uppercase tracking-wide text-streamwise-muted">Likes</p>
        <p className="text-2xl font-semibold">{likeCount}</p>
        <p className="text-xs text-streamwise-muted">
          {likeCount === 1 ? "Community like" : "Community likes"}
        </p>
      </div>
    </div>
  );
}
