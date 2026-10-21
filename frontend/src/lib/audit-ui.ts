import type { LucideIcon } from "lucide-react";
import { Bot, ClipboardCheck, Cog, Shield, User } from "lucide-react";
import { formatUSD } from "./api";
import type { Actor, AuditEntry } from "./types";

export const actorMeta: Record<
  Actor,
  { label: string; icon: LucideIcon; chip: string }
> = {
  user: {
    label: "You",
    icon: User,
    chip: "bg-foreground/10 text-foreground/80",
  },
  buyer_agent: {
    label: "Buyer Agent",
    icon: Bot,
    chip: "bg-accent/15 text-[#8a6420] dark:text-accent",
  },
  guard: {
    label: "Guard",
    icon: Shield,
    chip: "bg-ask/25 text-[#8a5a00] dark:text-ask",
  },
  verifier: {
    label: "Verifier",
    icon: ClipboardCheck,
    chip: "bg-approve/15 text-[#16805a] dark:text-approve",
  },
  system: {
    label: "System",
    icon: Cog,
    chip: "bg-foreground/10 text-foreground/70",
  },
};

export type AuditFilter = "all" | Actor;

export const FILTERS: { key: AuditFilter; label: string }[] = [
  { key: "all", label: "All events" },
  { key: "buyer_agent", label: "Buyer Agent" },
  { key: "guard", label: "Guard" },
  { key: "verifier", label: "Verifier" },
  { key: "system", label: "System" },
];

// Column layout for wide screens (used by the header and every row)
export const AUDIT_COLUMNS =
  "md:grid md:grid-cols-[96px_150px_minmax(0,1.1fr)_110px_minmax(0,1.3fr)_24px] md:gap-x-4";

const words = (s: string) => s.replace(/_/g, " ");
const isNum = (v: unknown): v is number => typeof v === "number";

// Turns an entry's free-form details into labelled lines
export function detailItems(entry: AuditEntry): [string, string][] {
  const d = entry.details;
  const items: [string, string][] = [["Payment", entry.payment_id]];

  const amount = d.amount_cents;
  const risk = d.risk_score;
  const hard = d.hard_rule;
  const passed = d.passed;
  const total = d.total;
  const oldScore = d.old_score;
  const newScore = d.new_score;

  if (isNum(amount)) items.push(["Amount", formatUSD(amount)]);
  if (isNum(risk)) items.push(["Risk score", `${risk} / 100`]);
  if (typeof hard === "string") items.push(["Fixed rule that decided it", words(hard)]);
  if (isNum(passed) && isNum(total)) items.push(["Tests passed", `${passed} of ${total}`]);
  if (isNum(oldScore) && isNum(newScore)) items.push(["Trust score", `${oldScore} → ${newScore}`]);

  const known = new Set([
    "amount_cents",
    "risk_score",
    "hard_rule",
    "passed",
    "total",
    "old_score",
    "new_score",
  ]);
  for (const [key, value] of Object.entries(d)) {
    if (known.has(key)) continue;
    if (
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean"
    ) {
      items.push([words(key), String(value)]);
    }
  }
  return items;
}

export function auditToCsv(entries: AuditEntry[]): string {
  const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
  const header = ["Time", "Who", "What happened", "Decision", "Reason", "Payment"];
  const rows = entries.map((e) =>
    [
      e.at,
      actorMeta[e.actor].label,
      e.action,
      e.verdict ?? "",
      e.reason,
      e.payment_id,
    ]
      .map(esc)
      .join(",")
  );
  return [header.map(esc).join(","), ...rows].join("\n");
}