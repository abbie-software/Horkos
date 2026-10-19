import StatusPill from "@/components/StatusPill";
import { formatUSD } from "@/lib/api";
import { initials } from "@/lib/format";
import type { Payment } from "@/lib/types";

function avatarClass(status: Payment["status"]) {
  if (status === "blocked") return "bg-block/15 text-[#b3303c] dark:text-block";
  if (status === "awaiting_user") return "bg-ask/25 text-[#8a5a00] dark:text-ask";
  return "bg-foreground/10 text-foreground/70";
}

export default function PaymentList({
  payments,
  selectedId,
  loading,
  onSelect,
}: {
  payments: Payment[];
  selectedId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
}) {
  const heldCents = payments
    .filter((p) => p.status === "held")
    .reduce((sum, p) => sum + p.amount_cents, 0);
  const waiting = payments.filter((p) => p.status === "awaiting_user").length;

  return (
    <div className="rounded-2xl border border-border bg-card p-4 sm:p-5">
      <h2 className="mb-4 font-serif text-lg font-semibold sm:text-xl">
        Active &amp; Recent Payments
      </h2>

      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 animate-pulse rounded-lg bg-foreground/5"
            />
          ))}
        </div>
      ) : payments.length === 0 ? (
        <p className="rounded-lg bg-foreground/5 p-6 text-center text-sm text-muted">
          No payments yet. Start a job above and it will appear here.
        </p>
      ) : (
        <ul className="space-y-1">
          {payments.map((p) => {
            const selected = p.id === selectedId;
            const lastNote = p.history[p.history.length - 1]?.note ?? "";
            return (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => onSelect(p.id)}
                  aria-current={selected}
                  className={`flex w-full items-center gap-3 rounded-lg border-l-4 px-3 py-3 text-left transition-colors ${
                    selected
                      ? "border-accent bg-accent/10"
                      : "border-transparent hover:bg-foreground/5"
                  }`}
                >
                  <span
                    className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${avatarClass(p.status)}`}
                  >
                    {initials(p.seller_name)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">
                      {p.seller_name}
                    </span>
                    <span className="block truncate text-xs text-muted">
                      {lastNote}
                    </span>
                  </span>
                  <span className="flex flex-col items-end gap-1 sm:flex-row sm:items-center sm:gap-4">
                    <span className="font-mono text-sm font-semibold sm:w-20 sm:text-right">
                      {formatUSD(p.amount_cents)}
                    </span>
                    <StatusPill status={p.status} />
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-border pt-4 text-sm">
        <p>
          <span className="text-muted">Held right now: </span>
          <span className="font-mono font-semibold">{formatUSD(heldCents)}</span>
        </p>
        <p className="text-xs text-muted">
          {waiting > 0
            ? `${waiting} waiting for your decision`
            : "Nothing waiting for you"}
        </p>
      </div>
    </div>
  );
}