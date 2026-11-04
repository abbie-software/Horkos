import { Check, ShieldCheck, TriangleAlert, X } from "lucide-react";
import StatusPill from "@/components/StatusPill";
import { formatUSD } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import {
  getLifecycle,
  riskTone,
  signalLabels,
  toneClasses,
  verdictMeta,
  type Step,
  type StepState,
} from "@/lib/payment-ui";
import type { Payment } from "@/lib/types";

function circleClass(state: StepState) {
  switch (state) {
    case "done":
      return "bg-approve text-white";
    case "current":
      return "bg-accent text-white";
    case "failed":
      return "bg-block text-white";
    default:
      return "border border-border bg-card text-muted";
  }
}

function lineClass(prev: Step, cur: Step) {
  if (prev.state !== "done") return "bg-border";
  if (cur.state === "failed") return "bg-block";
  return cur.state === "todo" ? "bg-border" : "bg-approve";
}

export default function PaymentDetail({
  payment,
  deciding,
  onDecide,
}: {
  payment: Payment | null;
  deciding: boolean;
  onDecide: (decision: "approve" | "reject") => void;
}) {
  if (!payment) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 text-center text-sm text-muted sm:p-8">
        Select a payment to see what the Guard decided and why.
      </div>
    );
  }

  const { decision } = payment;
  const verdict = verdictMeta[decision.verdict];
  const VerdictIcon = verdict.icon;
  const steps = getLifecycle(payment);
  const signals = [...decision.signals].sort(
    (a, b) => Number(b.triggered) - Number(a.triggered)
  );
  const canDecide = payment.status === "awaiting_user";

  return (
    <div className="space-y-5 rounded-2xl border border-border bg-card p-4 sm:p-5">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-serif text-xl font-semibold sm:text-2xl">
            {payment.seller_name}{" "}
            <span className="font-mono text-lg">
              {formatUSD(payment.amount_cents)}
            </span>
          </h2>
          <p className="mt-0.5 text-xs text-muted">
            Started {timeAgo(payment.created_at)}
          </p>
        </div>
        <StatusPill status={payment.status} />
      </div>

      {/* Lifecycle */}
      <div className="rounded-xl bg-foreground/5 p-4">
        <ol className="grid grid-cols-5">
          {steps.map((step, i) => (
            <li
              key={i}
              className="relative flex flex-col items-center text-center"
            >
              {i > 0 && (
                <span
                  className={`absolute left-[-50%] top-3.5 h-0.5 w-full ${lineClass(steps[i - 1], step)}`}
                />
              )}
              <span
                className={`relative z-10 flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold ${circleClass(step.state)}`}
              >
                {step.state === "done" ? (
                  <Check size={14} />
                ) : step.state === "failed" ? (
                  <X size={14} />
                ) : (
                  i + 1
                )}
              </span>
              <span
                className={`mt-2 text-[10px] leading-tight sm:text-xs ${
                  step.state === "todo" ? "text-muted" : "font-medium"
                }`}
              >
                {step.label}
              </span>
            </li>
          ))}
        </ol>
      </div>

      {/* Guard's verdict */}
      <section className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="flex items-center gap-2 font-serif text-lg font-semibold">
            <ShieldCheck size={18} className="text-accent" />
            Guard’s verdict
          </h3>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${toneClasses[verdict.tone]}`}
          >
            <VerdictIcon size={14} />
            {verdict.label}
          </span>
        </div>

        <div className="flex items-center gap-4 rounded-xl bg-foreground/5 p-4">
          <div
            className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full border-2 font-mono text-sm font-semibold ${riskTone[decision.risk_level]}`}
          >
            {decision.risk_score}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold capitalize">
              {decision.risk_level} risk
            </p>
            <p className="text-xs text-muted">
              Score {decision.risk_score} / 100
            </p>
          </div>
          <p className="text-right text-sm font-semibold text-accent">
            {verdict.note}
          </p>
        </div>

        <div className="rounded-xl bg-foreground/5 p-4 text-sm leading-relaxed">
          {decision.reason}
          {decision.hard_rule && (
            <p className="mt-2 text-xs text-muted">
              This is a fixed rule. The AI cannot override it.
            </p>
          )}
        </div>
      </section>

      {/* Signals */}
      <section>
        <h3 className="mb-2 text-sm font-semibold">Warning signs &amp; checks</h3>
        <ul className="grid gap-2 sm:grid-cols-2">
          {signals.map((s) => (
            <li
              key={s.code}
              className={`flex items-start gap-2 rounded-lg px-3 py-2 text-xs ${
                s.triggered ? "bg-ask/20" : "bg-foreground/5"
              }`}
            >
              {s.triggered ? (
                <TriangleAlert
                  size={15}
                  className="mt-0.5 shrink-0 text-[#b97400]"
                />
              ) : (
                <Check size={15} className="mt-0.5 shrink-0 text-approve" />
              )}
              <div className="min-w-0">
                <p className="font-medium">
                  {s.triggered
                    ? signalLabels[s.code].hit
                    : signalLabels[s.code].ok}
                </p>
                {s.triggered && (
                  <p className="mt-0.5 text-muted">{s.detail}</p>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>

            {(payment.paypal.funding_ref || payment.paypal.payout_ref || payment.paypal.refund_ref) && (
        <section>
          <h3 className="mb-2 text-sm font-semibold">PayPal</h3>
          <dl className="space-y-1 text-sm">
            {([
              [payment.paypal.funding_ref?.startsWith("SIM-") ? "Simulated funding" : "PayPal authorization", payment.paypal.funding_ref],
              ["Payout", payment.paypal.payout_ref],
              ["Refund", payment.paypal.refund_ref],
            ] as [string, string | null | undefined][]).map(([label, value]) =>
              value ? (
                <div key={label} className="flex justify-between gap-4">
                  <dt className="text-muted">{label}</dt>
                  <dd className="break-all text-right font-mono text-xs">{value}</dd>
                </div>
              ) : null
            )}
          </dl>
          {payment.status === "held" && payment.paypal.funding_ref && !payment.paypal.funding_ref.startsWith("SIM-") && (
            <p className="mt-2 text-xs text-muted">
              PayPal is holding the funds until the seller’s work is checked.
            </p>
          )}
        </section>
      )}

      {/* Approve / Reject (only when the Guard asked you) */}
      {canDecide && (
        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            disabled={deciding}
            onClick={() => onDecide("approve")}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-approve px-4 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            <Check size={16} />
            Approve {formatUSD(payment.amount_cents)}
          </button>
          <button
            type="button"
            disabled={deciding}
            onClick={() => onDecide("reject")}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-block/15 px-4 py-3 text-sm font-semibold text-[#b3303c] transition-opacity hover:opacity-80 disabled:opacity-50 dark:text-block"
          >
            <X size={16} />
            Reject
          </button>
        </div>
          )}
          {payment.status === "approved" && payment.paypal.approve_url && (
        <div className="space-y-3 rounded-xl bg-foreground/5 p-4">
          <p className="text-sm">
            Approved by the Guard. The next step is to fund this payment on
            PayPal’s sandbox. You will come back here afterwards.
          </p>
          <a
            href={payment.paypal.approve_url}
            className="inline-flex rounded-full bg-brand px-6 py-3 text-sm font-semibold text-brand-foreground active:scale-[0.97]"
          >
            Fund this payment
          </a>
        </div>
      )}
    </div>
  );
}