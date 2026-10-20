import { describeEvent } from "@/lib/event-ui";
import { toneClasses } from "@/lib/payment-ui";
import type { HorkosEvent } from "@/lib/types";

// 24-hour clock, for example 11:15:01
function clock(iso: string) {
  return new Date(iso).toLocaleTimeString("en-GB");
}

export default function EventRow({ event }: { event: HorkosEvent }) {
  const view = describeEvent(event);
  const Icon = view.icon;

  return (
    <li className="feed-in flex gap-3 rounded-xl border border-border bg-card p-3 sm:gap-4 sm:p-4">
      <span className="hidden w-16 shrink-0 pt-2 font-mono text-xs text-muted sm:block">
        {clock(event.at)}
      </span>
      <span
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${toneClasses[view.tone]}`}
      >
        <Icon size={17} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span
            className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${toneClasses[view.tone]}`}
          >
            {view.tag}
          </span>
          <span className="text-sm font-medium">{event.message}</span>
        </div>
        {view.detail && (
          <p className="mt-1 text-xs text-muted sm:text-sm">{view.detail}</p>
        )}
        <p className="mt-1 font-mono text-[11px] text-muted sm:hidden">
          {clock(event.at)}
        </p>
      </div>
    </li>
  );
}