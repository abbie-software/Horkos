"use client";

import { useState } from "react";
import { Play } from "lucide-react";
import type { Seller } from "@/lib/types";

export default function NewJobBar({
  sellers,
  starting,
  onStart,
}: {
  sellers: Seller[];
  starting: boolean;
  onStart: (text: string, sellerId?: string) => void;
}) {
  const [text, setText] = useState(
    "Write a Python function that converts a CSV file into JSON."
  );
  const [sellerId, setSellerId] = useState("");
  const canStart = text.trim().length > 0 && !starting;

  const field =
    "rounded-lg border border-border bg-background px-4 py-2.5 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/30";

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (canStart) onStart(text.trim(), sellerId || undefined);
      }}
      className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 sm:p-5 md:flex-row"
    >
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        aria-label="What do you want done?"
        placeholder="Describe the job you want done"
        className={`${field} min-w-0 flex-1`}
      />
      <select
        value={sellerId}
        onChange={(e) => setSellerId(e.target.value)}
        aria-label="Seller"
        className={`${field} md:w-52`}
      >
        <option value="">Seller: Auto-pick</option>
        {sellers.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>
      <button
        type="submit"
        disabled={!canStart}
        className="inline-flex items-center justify-center gap-2 rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        <Play size={16} />
        {starting ? "Starting…" : "Start job"}
      </button>
    </form>
  );
}