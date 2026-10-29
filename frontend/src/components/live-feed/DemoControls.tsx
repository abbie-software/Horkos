"use client";

import { useState } from "react";
import { Play, RefreshCw } from "lucide-react";
import { resetDemo, triggerAttack } from "@/lib/api";
import type { AttackType } from "@/lib/types";

const ATTACKS: { type: AttackType; label: string }[] = [
  { type: "recipient_change", label: "Change the recipient" },
  { type: "over_limit", label: "Go over the limit" },
  { type: "edge_of_limit", label: "Just under the limit" },
  { type: "rapid_retries", label: "Rapid retries" },
  { type: "pressure_language", label: "Pushy message" },
  { type: "bad_work", label: "Deliver bad work" },
];

export default function DemoControls({ onReset }: { onReset: () => void }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(type: AttackType, label: string) {
    setBusy(type);
    setNote(null);
    setError(null);
    try {
      await triggerAttack(type);
      setNote(`Started: ${label}. Watch the feed.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start the test.");
    } finally {
      setBusy(null);
    }
  }

  async function reset() {
    setBusy("reset");
    setNote(null);
    setError(null);
    try {
      await resetDemo();
      onReset();
      setNote("Demo reset.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reset the demo.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-sidebar p-5 text-sidebar-foreground">
      <div className="flex items-start justify-between gap-3">
        <h2 className="font-serif text-xl font-semibold text-white">
          Demo controls
        </h2>
      </div>
      <p className="mt-2 text-sm text-sidebar-muted">
        Play the part of a bad agent and watch the Guard respond.
      </p>

      <div className="mt-4 space-y-2">
        {ATTACKS.map((a) => (
          <button
            key={a.type}
            type="button"
            disabled={busy !== null}
            onClick={() => run(a.type, a.label)}
            className="flex w-full items-center justify-between rounded-lg bg-sidebar-active px-4 py-2.5 text-left text-sm font-medium transition-colors hover:bg-white/10 disabled:opacity-50"
          >
            {a.label}
            <Play size={14} className="text-sidebar-muted" />
          </button>
        ))}
      </div>

      <div className="mt-4 border-t border-white/10 pt-4">
        <button
          type="button"
          disabled={busy !== null}
          onClick={reset}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-white/15 px-4 py-2.5 text-sm font-medium transition-colors hover:bg-white/10 disabled:opacity-50"
        >
          <RefreshCw size={14} />
          Reset demo
        </button>
        <div aria-live="polite" className="mt-3 min-h-5 text-center text-xs">
          {note && <p className="text-sidebar-muted">{note}</p>}
          {error && <p className="text-[#ff8a93]">{error}</p>}
        </div>
        <p className="mt-1 text-center text-[11px] text-sidebar-muted">
          For demonstration only. Runs in the sandbox.
        </p>
      </div>
    </section>
  );
}