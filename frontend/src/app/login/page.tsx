"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { Mark } from "@/components/brand/Logo";

const DEMO = { email: "amara@example.com", password: "demo-password" };
const FIELD =
  "w-full rounded-lg border border-border bg-card px-4 py-2.5 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/30";

function destination(role?: string) {
  const next = new URLSearchParams(window.location.search).get("next");
  if (next && next.startsWith("/") && !next.startsWith("//")) return next;
  return role === "seller" ? "/seller" : "/money-tracker";
}

export default function LoginPage() {
  const { user, ready, signIn } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ready && user) router.replace(destination());
  }, [ready, user, router]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(email.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in. Please try again.");
      setBusy(false);
    }
  }

  return (
    <main className="rise flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <Link href="/" className="mb-8 flex items-center gap-3">
          <Mark className="h-10 w-10" />
          <span className="font-serif text-2xl font-semibold tracking-wide">Horkos</span>
        </Link>
        <h1 className="font-serif text-4xl tracking-tight">Sign in</h1>
        <p className="mt-2 text-sm text-muted">Use your Horkos account.</p>

        <form onSubmit={submit} className="mt-8 space-y-4">
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-medium">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={FIELD}
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1.5 block text-sm font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={FIELD}
            />
          </div>

          {error && (
            <p role="alert" className="rounded-lg bg-block/10 p-3 text-sm text-[#b3303c] dark:text-block">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-full bg-brand px-6 py-3 text-sm font-semibold text-brand-foreground active:scale-[0.97] disabled:opacity-50"
          >
            {busy ? "Signing in" : "Sign in"}
          </button>
        </form>

        <div className="mt-8 space-y-3 border-t border-border pt-6 text-sm text-muted">
          <p>
            Trying it out?{" "}
            <button
              type="button"
              onClick={() => {
                setEmail(DEMO.email);
                setPassword(DEMO.password);
              }}
              className="font-semibold text-foreground underline underline-offset-4"
            >
              Fill in the demo account
            </button>
            . It runs on the PayPal sandbox.
          </p>
          <p>New here? Sign-up is coming soon.</p>
          <p>
            Are you a seller?{" "}
            <Link href="/seller" className="font-semibold text-foreground underline underline-offset-4">
              Choose your seller
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}