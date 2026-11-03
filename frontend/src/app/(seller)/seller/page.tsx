"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { useSeller } from "@/components/seller/useSeller";
import { formatUSD, getJobs, getSellers, submitWork } from "@/lib/api";
import { initials } from "@/lib/format";
import type { Job, Seller } from "@/lib/types";
import { useAuth } from "@/components/AuthProvider";

const errorText = (e: unknown) =>
  e instanceof Error ? e.message : "Something went wrong. Please try again.";

function Skeleton() {
  return (
    <div className="space-y-2">
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-16 animate-pulse rounded-xl bg-foreground/5" />
      ))}
    </div>
  );
}

function ErrorBanner({ text }: { text: string }) {
  return (
    <p role="alert" className="mb-4 rounded-lg bg-block/10 p-3 text-sm text-[#b3303c] dark:text-block">
      {text}
    </p>
  );
}

function SellerPicker({ onChoose }: { onChoose: (id: string) => void }) {
  const [sellers, setSellers] = useState<Seller[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getSellers()
      .then((r) => {
        if (!cancelled) setSellers(r.items);
      })
      .catch((e) => {
        if (!cancelled) setError(errorText(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <PageHeader
        title="Choose who you are"
        subtitle="This is a demo. There is no password yet, so anyone can continue as any seller."
      />
      {error && <ErrorBanner text={error} />}
      {loading ? (
        <Skeleton />
      ) : (
        <ul className="divide-y divide-border rounded-2xl border border-border bg-card">
          {sellers.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                onClick={() => onChoose(s.id)}
                className="flex w-full items-center gap-4 p-4 text-left hover:bg-foreground/5 sm:p-5"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-foreground/10 text-sm font-semibold">
                  {initials(s.name)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-medium">{s.name}</span>
                  <span className="block text-sm capitalize text-muted">
                    {s.tier} seller, limit {formatUSD(s.limit_cents)}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function Workspace({ sellerId, onSwitch, actionLabel }: { sellerId: string; onSwitch: () => void; actionLabel: string }) {
  const [seller, setSeller] = useState<Seller | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getSellers(), getJobs(sellerId)])
      .then(([s, j]) => {
        if (cancelled) return;
        setSeller(s.items.find((x) => x.id === sellerId) ?? null);
        setJobs(j.items);
        setSelectedId(j.items[0]?.id ?? null);
      })
      .catch((e) => {
        if (!cancelled) setError(errorText(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sellerId]);

  const job = jobs.find((j) => j.id === selectedId) ?? null;
  const done = job ? sent.includes(job.id) : false;

  async function submit() {
    if (!job) return;
    setSending(true);
    setError(null);
    try {
      await submitWork(job.id, sellerId, code);
      setSent((list) => [...list, job.id]);
      setCode("");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <PageHeader
          title={seller ? seller.name : "Your jobs"}
          subtitle="Jobs waiting for your work. Read the tests, then submit your code."
        />
        <button
          type="button"
          onClick={onSwitch}
          className="rounded-full border border-border px-4 py-2 text-sm font-medium active:scale-[0.97]"
        >
          {actionLabel}
        </button>
      </div>

      {error && <ErrorBanner text={error} />}

      {loading ? (
        <Skeleton />
      ) : jobs.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted">
          No jobs are waiting for you right now.
        </p>
      ) : (
        <div className="grid gap-6 lg:grid-cols-5">
          <ul className="space-y-2 lg:col-span-2">
            {jobs.map((j) => (
              <li key={j.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(j.id)}
                  aria-current={j.id === selectedId}
                  className={`w-full rounded-xl border border-border p-4 text-left text-sm ${
                    j.id === selectedId ? "bg-accent/10" : "bg-card hover:bg-foreground/5"
                  }`}
                >
                  {j.request_text}
                  {sent.includes(j.id) && (
                    <span className="mt-1 block text-xs text-muted">Submitted</span>
                  )}
                </button>
              </li>
            ))}
          </ul>

          {job && (
            <section className="space-y-5 rounded-2xl border border-border bg-card p-4 sm:p-5 lg:col-span-3">
              <h2 className="font-serif text-xl font-semibold sm:text-2xl">
                {job.request_text}
              </h2>

              <div>
                <h3 className="text-sm font-semibold">Your code must pass these tests</h3>
                <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">
                  {job.acceptance_tests.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ol>
                <p className="mt-2 text-xs text-muted">
                  The first test names the function you need to write.
                </p>
              </div>

              {done ? (
                <p className="rounded-xl bg-approve/15 p-4 text-sm text-[#16805a] dark:text-approve">
                  Submitted. Horkos is checking your code now. See the result in the{" "}
                  <Link href="/live-feed" className="font-semibold underline">
                    Live Feed
                  </Link>
                  .
                </p>
              ) : (
                <>
                  <textarea
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    rows={10}
                    spellCheck={false}
                    aria-label="Your code"
                    placeholder="Paste your Python code here"
                    className="w-full resize-y rounded-xl border border-border bg-background p-4 font-mono text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
                  />
                  <button
                    type="button"
                    onClick={submit}
                    disabled={sending || code.trim().length === 0}
                    className="rounded-full bg-brand px-6 py-3 text-sm font-semibold text-brand-foreground active:scale-[0.97] disabled:opacity-50"
                  >
                    {sending ? "Submitting" : "Submit work"}
                  </button>
                </>
              )}
            </section>
          )}
        </div>
      )}
    </>
  );
}

export default function SellerPage() {
  const { user, ready, signOut } = useAuth();
  const { sellerId, ready: pickReady, choose } = useSeller();
  const live = process.env.NEXT_PUBLIC_USE_MOCKS === "false";
  if (!ready || !pickReady) return null;

  // A signed-in seller account: use their own seller record
  if (user?.role === "seller" && user.seller_id) {
    return <Workspace sellerId={user.seller_id} onSwitch={signOut} actionLabel="Sign out" />;
  }

  // Real backend: only seller accounts may use this page
  if (live) {
    return (
      <div className="max-w-md space-y-4">
        <h1 className="font-serif text-3xl tracking-tight">Seller sign-in needed</h1>
        <p className="text-sm text-muted">
          This area is for seller accounts. Sign in with one to see your jobs.
        </p>
        <Link
          href="/login?next=/seller"
          className="inline-flex rounded-full bg-brand px-6 py-3 text-sm font-semibold text-brand-foreground active:scale-[0.97]"
        >
          Sign in
        </Link>
      </div>
    );
  }

  // Sample-data mode: keep the picker so you can preview the page
  return sellerId ? (
    <Workspace sellerId={sellerId} onSwitch={() => choose(null)} actionLabel="Switch seller" />
  ) : (
    <SellerPicker onChoose={choose} />
  );
}