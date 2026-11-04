"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { Mark } from "@/components/brand/Logo";
import { ApiRequestError } from "@/lib/api";

const FIELD =
  "w-full rounded-lg border border-border bg-card px-4 py-2.5 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/30";

function check(name: string, email: string, password: string, role: string, paypal: string) {
  if (!name.trim()) return "Please enter your name.";
  if (password.length < 8) return "Your password must be at least 8 characters.";
  if (password.length > 200) return "Your password can be at most 200 characters.";
  if (password.trim().length === 0) return "Your password cannot be only spaces.";
  if (password.trim().toLowerCase() === email.trim().toLowerCase()) {
    return "Your password cannot be the same as your email.";
  }
  if (role === "seller" && !paypal.trim()) return "Sellers need a PayPal email to be paid.";
  return null;
}

export default function SignupPage() {
  const { user, ready, signUp } = useAuth();
  const router = useRouter();
  const [role, setRole] = useState<"buyer" | "seller">("buyer");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [paypal, setPaypal] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ready && user) router.replace(user.role === "seller" ? "/seller" : "/oath");
  }, [ready, user, router]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const problem = check(name, email, password, role, paypal);
    if (problem) {
      setError(problem);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await signUp({
        name: name.trim(),
        email: email.trim(),
        password,
        role,
        ...(role === "seller" ? { paypal_email: paypal.trim() } : {}),
      });
    } catch (err) {
      if (err instanceof ApiRequestError && err.code === "email_taken") {
        setError("That email is already in use. Sign in instead.");
      } else {
        setError(err instanceof Error ? err.message : "Could not create your account.");
      }
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
        <h1 className="font-serif text-4xl tracking-tight">Create an account</h1>

        <div role="radiogroup" aria-label="Account type" className="mt-6 flex rounded-full bg-foreground/5 p-1">
          {(["buyer", "seller"] as const).map((r) => (
            <button
              key={r}
              type="button"
              role="radio"
              aria-checked={role === r}
              onClick={() => setRole(r)}
              className={`flex-1 rounded-full px-4 py-1.5 text-sm font-medium capitalize active:scale-[0.97] ${
                role === r ? "bg-card shadow-sm" : "text-muted"
              }`}
            >
              {r}
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="name" className="mb-1.5 block text-sm font-medium">Name</label>
            <input id="name" autoComplete="name" required value={name} onChange={(e) => setName(e.target.value)} className={FIELD} />
          </div>
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-medium">Email</label>
            <input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={FIELD} />
          </div>
          <div>
            <label htmlFor="password" className="mb-1.5 block text-sm font-medium">Password</label>
            <input id="password" type="password" autoComplete="new-password" required value={password} onChange={(e) => setPassword(e.target.value)} className={FIELD} />
            <p className="mt-1 text-xs text-muted">At least 8 characters.</p>
          </div>
          {role === "seller" && (
            <div>
              <label htmlFor="paypal" className="mb-1.5 block text-sm font-medium">PayPal sandbox email</label>
              <input id="paypal" type="email" required value={paypal} onChange={(e) => setPaypal(e.target.value)} className={FIELD} />
              <p className="mt-1 text-xs text-muted">Where your payouts go. New sellers start with a $10 limit.</p>
            </div>
          )}

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
            {busy ? "Creating account" : "Create account"}
          </button>
        </form>

        <p className="mt-8 border-t border-border pt-6 text-sm text-muted">
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-foreground underline underline-offset-4">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}