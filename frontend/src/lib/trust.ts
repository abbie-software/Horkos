import type { LucideIcon } from "lucide-react";
import { Info, Shield, ShieldAlert, ShieldCheck } from "lucide-react";
import type { Seller, SellerTier } from "./types";

// TODO: confirm these numbers with the backend developer.
// They come from the design and the mock data. Change them here only.
export const LADDER_STEPS: {
  tier: SellerTier;
  label: string;
  limit_cents: number;
  min: number;
  max: number;
}[] = [
  { tier: "new", label: "New", limit_cents: 1000, min: 0, max: 25 },
  { tier: "building", label: "Building", limit_cents: 2500, min: 26, max: 74 },
  { tier: "trusted", label: "Trusted", limit_cents: 5000, min: 75, max: 100 },
];

export const RESTRICTED = { label: "Restricted", limit_cents: 500 };

export const tierMeta: Record<
  SellerTier,
  {
    label: string;
    icon: LucideIcon;
    badge: string;
    ring: string;
    limitClass: string;
    noteClass: string;
    note: string;
  }
> = {
  trusted: {
    label: "Trusted",
    icon: ShieldCheck,
    badge: "bg-approve/15 text-[#16805a] dark:text-approve",
    ring: "stroke-approve",
    limitClass: "text-foreground",
    noteClass: "text-[#16805a] dark:text-approve",
    note: "Earned the highest limit with a clean record.",
  },
  building: {
    label: "Building",
    icon: Shield,
    badge: "bg-accent/15 text-[#8a6420] dark:text-accent",
    ring: "stroke-accent",
    limitClass: "text-foreground",
    noteClass: "text-[#8a6420] dark:text-accent",
    note: "Still building a record. The limit rises as jobs pass verification.",
  },
  new: {
    label: "New",
    icon: Info,
    badge: "bg-foreground/10 text-foreground/70",
    ring: "stroke-muted",
    limitClass: "text-foreground",
    noteClass: "text-muted",
    note: "No history yet, so the starting limit is low.",
  },
  restricted: {
    label: "Restricted",
    icon: ShieldAlert,
    badge: "bg-block/15 text-[#b3303c] dark:text-block",
    ring: "stroke-block",
    limitClass: "text-[#b3303c] dark:text-block",
    noteClass: "text-[#b3303c] dark:text-block",
    note: "Limit cut after a broken rule or failed work.",
  },
};

export function sellerSubtitle(s: Seller): string {
  const jobs = `${s.jobs_completed} job${s.jobs_completed === 1 ? "" : "s"} completed`;
  switch (s.tier) {
    case "trusted":
      return `Proven record • ${jobs}`;
    case "building":
      return `Building trust • ${jobs}`;
    case "new":
      return s.jobs_completed === 0 ? "New seller • No jobs yet" : `New seller • ${jobs}`;
    case "restricted":
      return `Restricted • ${s.jobs_failed} failed job${s.jobs_failed === 1 ? "" : "s"}`;
  }
}

// The step above this tier, or null if there isn't one
export function nextStep(tier: SellerTier) {
  const i = LADDER_STEPS.findIndex((s) => s.tier === tier);
  return i >= 0 ? (LADDER_STEPS[i + 1] ?? null) : null;
}