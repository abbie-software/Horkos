import type { LucideIcon } from "lucide-react";
import {
  Ban,
  CircleAlert,
  CircleCheck,
  Clock,
  Hand,
  Lock,
  RotateCcw,
} from "lucide-react";
import type {
  Payment,
  PaymentStatus,
  RiskLevel,
  SignalCode,
  Verdict,
} from "./types";

export type Tone = "approve" | "block" | "ask" | "neutral";

export const toneClasses: Record<Tone, string> = {
  approve: "bg-approve/15 text-[#16805a] dark:text-approve",
  block: "bg-block/15 text-[#b3303c] dark:text-block",
  ask: "bg-ask/25 text-[#8a5a00] dark:text-ask",
  neutral: "bg-foreground/10 text-foreground/70",
};

export const statusMeta: Record<
  PaymentStatus,
  { label: string; tone: Tone; icon: LucideIcon }
> = {
  proposed: { label: "Proposed", tone: "neutral", icon: Clock },
  awaiting_user: { label: "Needs approval", tone: "ask", icon: CircleAlert },
  approved: { label: "Approved", tone: "approve", icon: CircleCheck },
  held: { label: "Held", tone: "neutral", icon: Lock },
  verified: { label: "Verified", tone: "approve", icon: CircleCheck },
  released: { label: "Paid", tone: "approve", icon: CircleCheck },
  refunded: { label: "Refunded", tone: "neutral", icon: RotateCcw },
  blocked: { label: "Blocked", tone: "block", icon: Ban },
};

export const verdictMeta: Record<
  Verdict,
  { label: string; tone: Tone; note: string; icon: LucideIcon }
> = {
  approve: {
    label: "Approve",
    tone: "approve",
    note: "Auto-approved",
    icon: CircleCheck,
  },
  ask: { label: "Ask", tone: "ask", note: "Manual check", icon: Hand },
  block: {
    label: "Block",
    tone: "block",
    note: "Blocked automatically",
    icon: Ban,
  },
};

export const riskTone: Record<RiskLevel, string> = {
  low: "border-approve text-[#16805a] dark:text-approve",
  medium: "border-ask text-[#8a5a00] dark:text-ask",
  high: "border-block text-[#b3303c] dark:text-block",
};

// Plain-English wording for the six risk signals
export const signalLabels: Record<SignalCode, { ok: string; hit: string }> = {
  intent_mismatch: {
    ok: "Matches your request",
    hit: "Doesn’t match your request",
  },
  recipient_changed: { ok: "Same recipient", hit: "Recipient changed" },
  edge_of_limit: { ok: "Within your limits", hit: "At or over a limit" },
  velocity: { ok: "Normal pace", hit: "Many payments quickly" },
  unproven_seller: { ok: "Seller has a record", hit: "New or unproven seller" },
  pressure_language: { ok: "No pressure wording", hit: "Pressure wording" },
};

export type StepState = "done" | "current" | "todo" | "failed";
export interface Step {
  label: string;
  state: StepState;
}

// Turns a payment's status into the 5-step lifecycle bar
export function getLifecycle(payment: Payment): Step[] {
  const labels = ["Proposed", "Guard check", "Hold", "Verify", "Paid"];
  if (payment.status === "awaiting_user") labels[1] = "Needs approval";

  let current = 0;
  let failedAt = -1;

  switch (payment.status) {
    case "proposed":
    case "awaiting_user":
      current = 1;
      break;
    case "approved":
      current = 2;
      break;
    case "held":
      current = 3;
      break;
    case "verified":
      current = 4;
      break;
    case "released":
      current = 5;
      break;
    case "refunded":
      current = 3;
      failedAt = 3;
      break;
    case "blocked":
      current = 1;
      failedAt = 1;
      break;
  }

  return labels.map((label, i) => ({
    label,
    state:
      i === failedAt
        ? "failed"
        : i < current
          ? "done"
          : i === current
            ? "current"
            : "todo",
  }));
}