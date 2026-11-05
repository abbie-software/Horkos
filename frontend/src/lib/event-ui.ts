import type { LucideIcon } from "lucide-react";
import {
  Ban,
  Bug,
  CircleCheck,
  CircleX,
  Hand,
  RefreshCw,
  RotateCcw,
  Send,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { formatUSD } from "./api";
import { statusMeta, type Tone } from "./payment-ui";
import type { HorkosEvent, PaymentStatus } from "./types";

const num = (v: unknown): number | null => (typeof v === "number" ? v : null);
const str = (v: unknown): string | null => (typeof v === "string" ? v : null);
const words = (code: string) => code.replace(/_/g, " ");

export interface EventView {
  tag: string;
  tone: Tone;
  icon: LucideIcon;
  detail: string | null;
}

export function describeEvent(e: HorkosEvent): EventView {
  const p = e.payload;

  switch (e.type) {
    case "payment.proposed": {
      const cents = num(p.amount_cents);
      return {
        tag: "Proposed",
        tone: "neutral",
        icon: Send,
        detail: cents !== null ? `Amount ${formatUSD(cents)}` : null,
      };
    }

    case "payment.verdict": {
      const verdict = str(p.verdict);
      const level = str(p.risk_level);
      const score = num(p.risk_score);
      const hard = str(p.hard_rule);
      const parts: string[] = [];
      if (level && score !== null) {
        parts.push(
          `${level.charAt(0).toUpperCase()}${level.slice(1)} risk (${score}/100)`
        );
      }
      if (hard) parts.push(`Fixed rule: ${words(hard)}`);
      const detail = parts.length > 0 ? parts.join(" • ") : null;

      if (verdict === "block") {
        return { tag: "Blocked", tone: "block", icon: Ban, detail };
      }
      if (verdict === "ask") {
        return { tag: "Ask", tone: "ask", icon: Hand, detail };
      }
      return { tag: "Approved", tone: "approve", icon: ShieldCheck, detail };
    }

    case "payment.status_changed": {
      const to = str(p.to);
      if (to && to in statusMeta) {
        const meta = statusMeta[to as PaymentStatus];
        return { tag: meta.label, tone: meta.tone, icon: meta.icon, detail: null };
      }
      return { tag: "Updated", tone: "neutral", icon: RefreshCw, detail: null };
    }

    case "verification.result": {
      const passedCount = num(p.tests_passed);
      const total = num(p.tests_total);
      const detail =
        passedCount !== null && total !== null
          ? `${passedCount} of ${total} tests passed`
          : null;
      return p.passed === true
        ? { tag: "Verified", tone: "approve", icon: CircleCheck, detail }
        : { tag: "Failed", tone: "block", icon: CircleX, detail };
    }

    case "trust.updated": {
      const oldScore = num(p.old_score);
      const newScore = num(p.new_score);
      const limit = num(p.new_limit_cents);
      const up = oldScore !== null && newScore !== null ? newScore >= oldScore : true;
      const parts: string[] = [];
      if (oldScore !== null && newScore !== null) {
        parts.push(`Trust score ${oldScore} → ${newScore}`);
      }
      if (limit !== null) parts.push(`New limit ${formatUSD(limit)}`);
      return {
        tag: "Trust",
        tone: up ? "approve" : "block",
        icon: up ? TrendingUp : TrendingDown,
        detail: parts.length > 0 ? parts.join(" • ") : null,
      };
    }

    case "demo.attack_started":
      return {
        tag: "Simulation",
        tone: "ask",
        icon: Bug,
        detail: "Started from the demo controls",
      };

    case "demo.reset":
      return { tag: "Reset", tone: "neutral", icon: RotateCcw, detail: null };
  }
}