"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import NewJobBar from "@/components/money-tracker/NewJobBar";
import PaymentList from "@/components/money-tracker/PaymentList";
import PaymentDetail from "@/components/money-tracker/PaymentDetail";
import {
  ApiRequestError,
  createJob,
  decidePayment,
  getPayments,
  getSellers,
} from "@/lib/api";
import type { Payment, Seller } from "@/lib/types";

function errorText(e: unknown) {
  return e instanceof Error ? e.message : "Something went wrong. Please try again.";
}

export default function MoneyTrackerPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [needsOath, setNeedsOath] = useState(false);
  const [deciding, setDeciding] = useState(false);
  const [starting, setStarting] = useState(false);
  const detailRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [paymentRes, sellerRes] = await Promise.all([
          getPayments(),
          getSellers(),
        ]);
        if (cancelled) return;
        setPayments(paymentRes.items);
        setSellers(sellerRes.items);
        const first =
          paymentRes.items.find((p) => p.status === "awaiting_user") ??
          paymentRes.items[0];
        setSelectedId(first ? first.id : null);
      } catch (e) {
        if (!cancelled) setError(errorText(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const selected = payments.find((p) => p.id === selectedId) ?? null;

  function handleSelect(id: string) {
    setSelectedId(id);
    // On phones and tablets the details sit below the list, so scroll to them
    if (window.innerWidth < 1280) {
      detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  async function handleDecide(decision: "approve" | "reject") {
    if (!selected) return;
    setDeciding(true);
    setError(null);
    try {
      const updated = await decidePayment(selected.id, decision);
      setPayments((list) =>
        list.map((p) => (p.id === updated.id ? updated : p))
      );
    } catch (e) {
      setError(errorText(e));
    } finally {
      setDeciding(false);
    }
  }

  async function handleStart(text: string, sellerId?: string) {
    setStarting(true);
    setError(null);
    setNeedsOath(false);
    try {
      const { payment } = await createJob(text, sellerId);
      setPayments((list) => [payment, ...list.filter((p) => p.id !== payment.id)]);
      handleSelect(payment.id);
    } catch (e) {
      if (e instanceof ApiRequestError && e.status === 409) {
        setNeedsOath(true);
      } else {
        setError(errorText(e));
      }
    } finally {
      setStarting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Money Tracker"
        subtitle="Follow every payment from proposal to payout."
      />

      {error && (
        <div
          role="alert"
          className="mb-4 rounded-lg bg-block/10 p-3 text-sm text-[#b3303c] dark:text-block"
        >
          {error}
        </div>
      )}

      <NewJobBar sellers={sellers} starting={starting} onStart={handleStart} />

      {starting && (
        <p aria-live="polite" className="mt-3 text-sm text-muted">
          The Buyer Agent is choosing a seller and the Guard is checking the
          payment. This takes a few seconds…
        </p>
      )}
      {needsOath && (
        <div role="alert" className="mt-3 rounded-lg bg-ask/20 p-3 text-sm">
          Save your oath first. Horkos needs your rules before it can check a
          payment.{" "}
          <Link href="/oath" className="font-semibold underline">
            Go to the Oath page
          </Link>
        </div>
      )}

      <div className="mt-6 grid gap-6 xl:grid-cols-5">
        <div className="xl:col-span-3">
          <PaymentList
            payments={payments}
            selectedId={selectedId}
            loading={loading}
            onSelect={handleSelect}
          />
        </div>
        <div
          ref={detailRef}
          className="scroll-mt-20 xl:col-span-2 xl:sticky xl:top-6 xl:self-start"
        >
          <PaymentDetail
            payment={selected}
            deciding={deciding}
            onDecide={handleDecide}
          />
        </div>
      </div>
    </>
  );
}