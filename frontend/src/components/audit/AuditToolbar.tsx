import { Search } from "lucide-react";
import { FILTERS, type AuditFilter } from "@/lib/audit-ui";

export default function AuditToolbar({
  filter,
  query,
  onFilter,
  onQuery,
}: {
  filter: AuditFilter;
  query: string;
  onFilter: (f: AuditFilter) => void;
  onQuery: (q: string) => void;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex flex-wrap items-center gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => onFilter(f.key)}
            aria-pressed={filter === f.key}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              filter === f.key
                ? "bg-foreground text-background"
                : "text-muted hover:bg-foreground/5 hover:text-foreground"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>
      <label className="relative block lg:w-72">
        <span className="sr-only">Search events</span>
        <Search
          size={16}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
        />
        <input
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="Search events, agents, or rules…"
          className="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/30"
        />
      </label>
    </div>
  );
}