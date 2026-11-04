"use client";


import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import StatusPill from "@/components/StatusPill";
import { ApiRequestError, confirmFunding, formatUSD } from "@/lib/api";
import type { Payment } from "@/lib/types";

type View =
  | { kind: "working" }
  | { kind: "done"; payment: Payment }
  | { kind: "error"; message: string };

function explain(e: unknown): string {
  if (e instanceof ApiRequestError) {
    if (e.status === 422) {
      return "PayPal has not received your approval yet. Go back and press Fund this payment again.";
    }
    if (e.status === 409) {
      return "This payment is not waiting for funding. It may already be funded.";
    }
  }
  return e instanceof Error ? e.message : "Something went wrong. Please try again.";
}

export default function FundingReturnPage() {
  const [view, setView] = useState<View>({ kind: "working" });
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const id = new URLSearchParams(window.location.search).get("payment");
    if (!id) {
      setView({ kind: "error", message: "This link does not say which payment to confirm." });
      return;
    }
    confirmFunding(id)
      .then((payment) => setView({ kind: "done", payment }))
      .catch((e) => setView({ kind: "error", message: explain(e) }));
  }, []);

  return (
    <>
      <PageHeader title="Funding" subtitle="Confirming your payment with PayPal." />
      <div className="max-w-xl rounded-2xl border border-border bg-card p-5" aria-live="polite">
        {view.kind === "working" && (
          <p className="text-sm text-muted">Checking with PayPal. This takes a few seconds…</p>
        )}
        {view.kind === "done" && (
          <div className="space-y-3">
            <StatusPill status={view.payment.status} />
            <p className="text-sm">
              Funding confirmed for {view.payment.seller_name},{" "}
              {formatUSD(view.payment.amount_cents)}. The money stays held until
              the seller’s work is checked.
            </p>
          </div>
        )}
        {view.kind === "error" && (
          <p role="alert" className="text-sm text-[#b3303c] dark:text-block">
            {view.message}
          </p>
        )}
        <Link
          href="/money-tracker"
          className="mt-5 inline-flex rounded-full border border-border px-5 py-2 text-sm font-semibold active:scale-[0.97]"
        >
          Back to the Money Tracker
        </Link>
      </div>
    </>
  );
}