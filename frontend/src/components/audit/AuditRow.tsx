import { ChevronDown } from "lucide-react";
import { actorMeta, AUDIT_COLUMNS, detailItems } from "@/lib/audit-ui";
import { toneClasses, verdictMeta } from "@/lib/payment-ui";
import type { AuditEntry } from "@/lib/types";

export default function AuditRow({
  entry,
  open,
  onToggle,
}: {
  entry: AuditEntry;
  open: boolean;
  onToggle: () => void;
}) {
  const actor = actorMeta[entry.actor];
  const ActorIcon = actor.icon;
  const verdict = entry.verdict ? verdictMeta[entry.verdict] : null;
  const VerdictIcon = verdict ? verdict.icon : null;
  const when = new Date(entry.at);

  return (
    <li className={open ? "bg-foreground/5" : ""}>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="w-full px-4 py-3 text-left transition-colors hover:bg-foreground/5"
      >
        <div
          className={`flex flex-wrap items-center gap-x-3 gap-y-1.5 md:items-center ${AUDIT_COLUMNS}`}
        >
          <div className="order-1 md:order-none">
            <p className="font-mono text-sm">{when.toLocaleTimeString("en-GB")}</p>
            <p className="text-[11px] text-muted">
              {when.toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
            </p>
          </div>

          <div className="order-2 md:order-none">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${actor.chip}`}
            >
              <ActorIcon size={13} />
              {actor.label}
            </span>
          </div>

          <p className="order-4 w-full text-sm font-medium md:order-none md:w-auto">
            {entry.action}
          </p>

          <div className="order-5 md:order-none">
            {verdict && VerdictIcon ? (
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${toneClasses[verdict.tone]}`}
              >
                <VerdictIcon size={13} />
                {verdict.label}
              </span>
            ) : (
              <span className="hidden text-muted md:inline">—</span>
            )}
          </div>

          <p className="order-6 w-full text-sm text-muted md:order-none md:w-auto">
            {entry.reason}
          </p>

          <ChevronDown
            size={18}
            className={`order-3 ml-auto text-muted transition-transform md:order-none md:ml-0 ${
              open ? "rotate-180" : ""
            }`}
          />
        </div>
      </button>

      {open && (
        <div className="border-t border-border px-4 py-4 md:px-6">
          <p className="mb-3 text-xs text-muted">{when.toLocaleString()}</p>
          <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {detailItems(entry).map(([label, value]) => (
              <div key={label} className="rounded-lg bg-foreground/5 px-3 py-2">
                <dt className="text-[11px] font-semibold uppercase tracking-wider text-muted">
                  {label}
                </dt>
                <dd className="mt-0.5 break-words text-sm font-medium ">
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </li>
  );
}