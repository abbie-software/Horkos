"use client";


import { useEffect, useState } from "react";
import PageHeader from "@/components/PageHeader";
import { resetDemo } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";

type Mode = "light" | "dark" | "system";

function applyTheme(mode: Mode) {
  const dark =
    mode === "dark" ||
    (mode === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
  try {
    if (mode === "system") localStorage.removeItem("horkos-theme");
    else localStorage.setItem("horkos-theme", mode);
  } catch {}
}

export default function SettingsPage() {
  const { user } = useAuth();
  const [mode, setMode] = useState<Mode>("system");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const live = process.env.NEXT_PUBLIC_USE_MOCKS === "false";

  useEffect(() => {
    try {
      const saved = localStorage.getItem("horkos-theme");
      setMode(saved === "dark" || saved === "light" ? saved : "system");
    } catch {}
  }, []);

  async function reset() {
    setBusy(true);
    setNote(null);
    try {
      await resetDemo();
      setNote("Demo data reset.");
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Could not reset the demo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Settings" subtitle="How Horkos looks and where its data comes from." />
      <div className="divide-y divide-border rounded-2xl border border-border bg-card">
        <section className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div>
            <h2 className="font-serif text-lg font-semibold">Appearance</h2>
            <p className="text-sm text-muted">System follows your device.</p>
          </div>
          <div role="radiogroup" aria-label="Theme" className="flex rounded-full bg-foreground/5 p-1">
            {(["light", "dark", "system"] as Mode[]).map((m) => (
              <button
                key={m}
                type="button"
                role="radio"
                aria-checked={mode === m}
                onClick={() => {
                  setMode(m);
                  applyTheme(m);
                }}
                className={`rounded-full px-4 py-1.5 text-sm font-medium capitalize active:scale-[0.97] ${
                  mode === m ? "bg-card shadow-sm" : "text-muted"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </section>

        <section className="p-5">
          <h2 className="font-serif text-lg font-semibold">Data source</h2>
          <p className="text-sm text-muted">
            {live ? "Connected to the Horkos backend." : "Showing built-in sample data. No backend is connected."}
          </p>
        </section>

        <section className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div>
            <h2 className="font-serif text-lg font-semibold">Demo data</h2>
            <p className="text-sm text-muted" aria-live="polite">
              {note ?? "Return the demo to its starting state. Accounts made through sign-up are removed."}
            </p>
          </div>
          <button
            type="button"
            disabled={busy}
            onClick={reset}
            className="rounded-full border border-border px-5 py-2 text-sm font-semibold active:scale-[0.97] disabled:opacity-50"
          >
            {busy ? "Resetting" : "Reset demo"}
          </button>
        </section>

        <section className="p-5">
          <h2 className="font-serif text-lg font-semibold">Account</h2>
          <p className="text-sm text-muted">Signed in as {user?.name} ({user?.email}).</p>
        </section>
      </div>
    </>
  );
}