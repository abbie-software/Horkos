import {  Plus, RotateCcw, ShieldCheck } from "lucide-react";

const SUGGESTIONS = [
  "Never spend over $50 per job.",
  "Spend at most $100 per day.",
  "Ask me before anything over $30.",
  "Always ask me about a seller I have not used before.",
  "Only allow coding work.",
];

function addClause(text: string, clause: string) {
  const trimmed = text.trim();
  if (trimmed.includes(clause)) return text;
  return trimmed ? `${trimmed} ${clause}` : clause;
}

export default function OathEditor({
  text,
  loading,
  saving,
  dirty,
  note,
  error,
  onChange,
  onSave,
  onReset,
}: {
  text: string;
  loading: boolean;
  saving: boolean;
  dirty: boolean;
  note: string | null;
  error: string | null;
  onChange: (value: string) => void;
  onSave: () => void;
  onReset: () => void;
}) {
  const canSave = !loading && !saving && dirty && text.trim().length > 0;

  return (
    <section className="rounded-2xl border border-border bg-card p-4 sm:p-5">
      <h2 className="flex items-center gap-2 font-serif text-lg font-semibold sm:text-xl">
        Write your oath
      </h2>

      <textarea
        value={text}
        onChange={(e) => onChange(e.target.value)}
        disabled={loading}
        rows={6}
        aria-label="Your oath in plain English"
        placeholder="Example: Spend up to $50 per job and $100 per day. Only on coding work."
        className="mt-4 w-full resize-y rounded-xl border border-border bg-background p-4 text-sm leading-relaxed outline-none focus:border-accent focus:ring-2 focus:ring-accent/30 disabled:opacity-60"
      />

      <p className="mt-4 text-xs font-medium text-muted">Suggested clauses</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            disabled={loading}
            onClick={() => onChange(addClause(text, s))}
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1.5 text-left text-xs hover:border-accent hover:bg-accent/10 disabled:opacity-50"
          >
            <Plus size={12} className="shrink-0 text-accent" />
            {s}
          </button>
        ))}
      </div>
            <p className="mt-3 text-xs text-muted">
        Work types Horkos understands: coding, writing, design, data and other.
        Use these words, for example “Only coding work.”
      </p>

      {error && (
        <div
          role="alert"
          className="mt-4 rounded-lg bg-block/10 p-3 text-sm text-[#b3303c] dark:text-block"
        >
          {error}
        </div>
      )}

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <p className="flex items-center gap-2 text-sm" aria-live="polite">
          <span
            className={`h-2 w-2 rounded-full ${dirty ? "bg-ask" : "bg-approve"}`}
          />
          {dirty ? "Unsaved changes" : (note ?? "Saved oath is in effect")}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onReset}
            disabled={!dirty || saving}
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-muted hover:text-foreground disabled:opacity-40"
          >
            <RotateCcw size={14} />
            Reset
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={!canSave}
            className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            <ShieldCheck size={16} />
            {saving ? "Saving…" : "Save oath"}
          </button>
        </div>
      </div>
    </section>
  );
}