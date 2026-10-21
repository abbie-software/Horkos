import type { LucideIcon } from "lucide-react";
import { Ban, Bell, Briefcase, Clock, Code, UserPlus } from "lucide-react";
import { formatUSD } from "@/lib/api";
import type { Policy } from "@/lib/types";

interface Row {
  icon: LucideIcon;
  title: string;
  text: string;
}

function buildRows(policy: Policy): Row[] {
  const rows: Row[] = [
    {
      icon: Briefcase,
      title: `Per-job cap: ${formatUSD(policy.per_job_cap_cents)}`,
      text: `Any payment above ${formatUSD(policy.per_job_cap_cents)} is blocked automatically.`,
    },
    {
      icon: Clock,
      title: `Daily cap: ${formatUSD(policy.daily_cap_cents)}`,
      text: "Payments that would push the day’s total past this are blocked.",
    },
    {
      icon: Bell,
      title: `Approval needed above ${formatUSD(policy.ask_threshold_cents)}`,
      text: "The Guard asks you before paying more than this.",
    },
    policy.allowed_categories.length > 0
      ? {
          icon: Code,
          title: `Allowed work: ${policy.allowed_categories.join(", ")}`,
          text: "Other kinds of work are blocked.",
        }
      : {
          icon: Code,
          title: "Allowed work: any kind",
          text: "No type of work is ruled out.",
        },
  ];

  if (policy.blocked_categories.length > 0) {
    rows.push({
      icon: Ban,
      title: `Never allowed: ${policy.blocked_categories.join(", ")}`,
      text: "Payments for these are always blocked.",
    });
  }

  rows.push(
    policy.ask_for_new_sellers
      ? {
          icon: UserPlus,
          title: "New sellers need your approval",
          text: "A seller you haven’t used before waits for you.",
        }
      : {
          icon: UserPlus,
          title: "New sellers don’t need approval",
          text: "They are checked like everyone else.",
        }
  );

  return rows;
}

export default function PolicySummary({
  policy,
  dirty,
}: {
  policy: Policy | null;
  dirty: boolean;
}) {
  return (
    <section className="rounded-2xl border border-border bg-card p-4 sm:p-5">
      <h2 className="font-serif text-lg font-semibold sm:text-xl">
        What Horkos understood
      </h2>
      <p className="mt-1 text-sm text-muted">
        {dirty
          ? "You have unsaved changes. This list shows your saved oath."
          : "Check that these match what you meant."}
      </p>

      {!policy ? (
        <div className="mt-4 space-y-2">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-14 animate-pulse rounded-xl bg-foreground/5"
            />
          ))}
        </div>
      ) : (
        <ul className="mt-4 space-y-2">
          {buildRows(policy).map((row) => {
            const Icon = row.icon;
            return (
              <li
                key={row.title}
                className="flex items-start gap-3 rounded-xl bg-foreground/5 p-3"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-card text-accent">
                  <Icon size={17} />
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-semibold capitalize-first">
                    {row.title}
                  </p>
                  <p className="text-xs text-muted sm:text-sm">{row.text}</p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}