import Link from "next/link";
import { TrendingUp } from "lucide-react";
import { formatUSD } from "@/lib/api";
import { initials } from "@/lib/format";
import { nextStep } from "@/lib/trust";
import type { Seller } from "@/lib/types";

export default function NextPromotion({ sellers }: { sellers: Seller[] }) {
  // The seller closest to the next tier
  const candidate = sellers
    .filter((s) => nextStep(s.tier) !== null)
    .sort((a, b) => b.trust_score - a.trust_score)[0];
  const next = candidate ? nextStep(candidate.tier) : null;

  return (
    <section className="rounded-2xl border border-border bg-card p-4 sm:p-5">
      <h2 className="flex items-center gap-2 font-serif text-lg font-semibold sm:text-xl">
        <TrendingUp size={18} className="text-accent" />
        Next promotion
      </h2>

      {!candidate || !next ? (
        <p className="mt-4 rounded-xl bg-foreground/5 p-4 text-sm text-muted">
          Every active seller is already at the top tier.
        </p>
      ) : (
        <>
          <div className="mt-4 flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-foreground/10 text-sm font-semibold">
              {initials(candidate.name)}
            </span>
            <div>
              <p className="text-sm font-semibold">{candidate.name}</p>
              <p className="text-xs text-muted">
                On the way to {next.label}
              </p>
            </div>
          </div>

          <div className="mt-4">
            <div className="mb-1 flex justify-between text-xs text-muted">
              <span>Trust score</span>
              <span className="font-mono">
                {candidate.trust_score} / {next.min}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-foreground/10">
              <div
                className="h-full rounded-full bg-accent"
                style={{
                  width: `${Math.min(candidate.trust_score / next.min, 1) * 100}%`,
                }}
              />
            </div>
          </div>

          <p className="mt-4 rounded-xl bg-foreground/5 p-4 text-sm leading-relaxed">
            Needs {Math.max(next.min - candidate.trust_score, 0)} more points to
            reach {next.label}. The limit would then rise from{" "}
            <span className="font-semibold">
              {formatUSD(candidate.limit_cents)}
            </span>{" "}
            to{" "}
            <span className="font-semibold">{formatUSD(next.limit_cents)}</span>.
          </p>
        </>
      )}

      <Link
        href="/live-feed"
        className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-[#8a6420] hover:underline dark:text-accent"
      >
        Watch trust change in the Live Feed
        
      </Link>
    </section>
  );
}