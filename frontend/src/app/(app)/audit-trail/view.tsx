"use client";


import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import AuditRow from "@/components/audit/AuditRow";
import AuditToolbar from "@/components/audit/AuditToolbar";
import { getAudit } from "@/lib/api";
import {
  actorMeta,
  AUDIT_COLUMNS,
  auditToCsv,
  type AuditFilter,
} from "@/lib/audit-ui";
import type { AuditEntry } from "@/lib/types";

function searchText(e: AuditEntry) {
  const hard =
    typeof e.details.hard_rule === "string"
      ? e.details.hard_rule.replace(/_/g, " ")
      : "";
  return [e.action, e.reason, actorMeta[e.actor].label, e.verdict ?? "", e.payment_id, hard]
    .join(" ")
    .toLowerCase();
}

export default function AuditTrailPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<AuditFilter>("all");
  const [query, setQuery] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getAudit()
      .then((res) => {
        if (!cancelled) setEntries(res.items);
      })
      .catch((e) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Something went wrong.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const q = query.trim().toLowerCase();
  const visible = [...entries]
    .sort((a, b) => b.at.localeCompare(a.at))
    .filter(
      (e) =>
        (filter === "all" || e.actor === filter) &&
        (q === "" || searchText(e).includes(q))
    );

  function handleExport() {
    const blob = new Blob([auditToCsv(visible)], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "horkos-audit-log.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <PageHeader
        title="Audit Trail"
        subtitle="Every decision, with the reason."
      />

      {error && (
        <div
          role="alert"
          className="mb-4 rounded-lg bg-block/10 p-3 text-sm text-[#b3303c] dark:text-block"
        >
          {error}
        </div>
      )}

      <AuditToolbar
        filter={filter}
        query={query}
        onFilter={setFilter}
        onQuery={setQuery}
      />

      <div className="mt-4 overflow-hidden rounded-2xl border border-border bg-card">
        <div
          className={`hidden bg-foreground/5 px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-muted ${AUDIT_COLUMNS}`}
        >
          <span>Time</span>
          <span>Who</span>
          <span>What happened</span>
          <span>Decision</span>
          <span>Reason</span>
          <span />
        </div>

        {loading ? (
          <div className="space-y-2 p-4">
            {[0, 1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-14 animate-pulse rounded-lg bg-foreground/5"
              />
            ))}
          </div>
        ) : visible.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted">
            No events match. Try a different filter or search.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {visible.map((e) => (
              <AuditRow
                key={e.id}
                entry={e}
                open={openId === e.id}
                onToggle={() => setOpenId(openId === e.id ? null : e.id)}
              />
            ))}
          </ul>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border bg-foreground/5 px-4 py-3 text-sm">
          <p className="text-muted">
            Showing {visible.length} of {entries.length} events
          </p>
          <button
            type="button"
            onClick={handleExport}
            disabled={visible.length === 0}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 font-medium hover:bg-foreground/5 disabled:opacity-50"
          >
            <Download size={15} />
            Export audit log
          </button>
        </div>
      </div>
    </>
  );
}