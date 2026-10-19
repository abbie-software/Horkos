import { formatUSD } from "@/lib/api";
import { initials, timeAgo } from "@/lib/format";
import { sellerSubtitle, tierMeta } from "@/lib/trust";
import type { Seller } from "@/lib/types";
import ScoreRing from "./ScoreRing";

export default function SellerCard({ seller }: { seller: Seller }) {
  const meta = tierMeta[seller.tier];
  const TierIcon = meta.icon;

  return (
    <article className="rounded-2xl border border-border bg-card p-4 sm:p-5">
      <header className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-foreground/10 text-sm font-semibold">
            {initials(seller.name)}
          </span>
          <div className="min-w-0">
            <h2 className="truncate font-serif text-lg font-semibold">
              {seller.name}
            </h2>
            <p className="truncate text-xs text-muted">
              {sellerSubtitle(seller)}
            </p>
          </div>
        </div>
        <span
          className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide ${meta.badge}`}
        >
          <TierIcon size={13} />
          {meta.label}
        </span>
      </header>

      <div className="mt-5 flex items-center gap-5">
        <ScoreRing score={seller.trust_score} strokeClass={meta.ring} />
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">
            Spending limit
          </p>
          <p className={`font-serif text-3xl font-bold ${meta.limitClass}`}>
            {formatUSD(seller.limit_cents)}
            <span className="ml-1 text-xs font-normal text-muted">USD</span>
          </p>
          <p className={`mt-1 text-sm ${meta.noteClass}`}>{meta.note}</p>
        </div>
      </div>

      <footer className="mt-5 flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-4 text-xs text-muted">
        <span>{seller.jobs_completed} completed</span>
        <span>{seller.jobs_failed} failed</span>
        <span>
          {seller.last_activity_at
            ? `Last active ${timeAgo(seller.last_activity_at)}`
            : "No activity yet"}
        </span>
      </footer>
    </article>
  );
}