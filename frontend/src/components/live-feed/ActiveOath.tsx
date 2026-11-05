"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatUSD, getOath } from "@/lib/api";
import type { Oath } from "@/lib/types";

export default function ActiveOath() {
  const [oath, setOath] = useState<Oath | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getOath()
      .then((o) => {
        if (!cancelled) setOath(o);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const rows: [string, string][] = oath
    ? [
        ["Per-job cap", formatUSD(oath.policy.per_job_cap_cents)],
        ["Daily cap", formatUSD(oath.policy.daily_cap_cents)],
        ["Ask me above", formatUSD(oath.policy.ask_threshold_cents)],
        [
          "New sellers",
          oath.policy.ask_for_new_sellers ? "Ask me first" : "No approval needed",
        ],
        [
          "Allowed work",
          oath.policy.allowed_categories.join(", ") || "Anything",
        ],
      ]
    : [];

  return (
    <section className="rounded-2xl border border-border bg-card p-5">
      <h2 className="font-serif text-lg font-semibold">Active oath</h2>

      {failed ? (
        <p className="mt-3 text-sm text-muted">Couldn’t load your oath.</p>
      ) : !oath ? (
        <div className="mt-3 space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-5 animate-pulse rounded bg-foreground/5" />
          ))}
        </div>
      ) : (
        <dl className="mt-3 divide-y divide-border text-sm">
          {rows.map(([label, value]) => (
            <div key={label} className="flex justify-between gap-4 py-2">
              <dt className="text-muted">{label}</dt>
              <dd className="text-right font-medium">{value}</dd>
            </div>
          ))}
        </dl>
      )}

      <Link
        href="/oath"
        className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-[#8a6420] hover:underline dark:text-accent"
      >
        Edit your oath
      </Link>
    </section>
  );
}