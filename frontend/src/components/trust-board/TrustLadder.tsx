import { TrendingDown } from "lucide-react";
import { formatUSD } from "@/lib/api";
import { LADDER_STEPS, RESTRICTED, tierMeta } from "@/lib/trust";

export default function TrustLadder() {
  return (
    <section className="rounded-2xl border border-border bg-card p-4 sm:p-5">
      <h2 className="font-serif text-lg font-semibold sm:text-xl">Trust Ladder</h2>
      <p className="mt-1 text-sm text-muted">
        Limits rise as sellers complete verified work.
      </p>

      <ol className="relative mt-6 grid grid-cols-3">
        <span
          aria-hidden="true"
          className="absolute left-[16.66%] right-[16.66%] top-5 h-0.5 bg-border"
        />
        {LADDER_STEPS.map((step) => {
          const meta = tierMeta[step.tier];
          const Icon = meta.icon;
          return (
            <li
              key={step.tier}
              className="relative flex flex-col items-center text-center"
            >
              <span className="relative z-10 rounded-full bg-card">
                <span
                  className={`flex h-10 w-10 items-center justify-center rounded-full ${meta.badge}`}
                >
                  <Icon size={18} />
                </span>
              </span>
              <span className={`mt-3 text-sm font-semibold ${meta.noteClass}`}>
                {step.label}
              </span>
              <span className="font-serif text-base font-bold sm:text-lg">
                {formatUSD(step.limit_cents)}
              </span>
              <span className="text-[11px] text-muted sm:text-xs">
                Score {step.min}–{step.max}
              </span>
            </li>
          );
        })}
      </ol>

      <div className="mt-6 flex items-start gap-3 rounded-xl bg-block/10 p-4">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-block/15 text-[#b3303c] dark:text-block">
          <TrendingDown size={16} />
        </span>
        <div className="text-sm">
          <p className="font-semibold text-[#b3303c] dark:text-block">
            Restricted tier ({formatUSD(RESTRICTED.limit_cents)} limit)
          </p>
          <p className="mt-0.5 text-muted">
            Applied straight away after a broken rule or a failed check.
          </p>
        </div>
      </div>

      <p className="mt-5 border-t border-border pt-4 text-xs text-muted">
        The Guard manages tiers automatically.
      </p>
    </section>
  );
}