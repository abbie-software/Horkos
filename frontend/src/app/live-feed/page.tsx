"use client";

import { useEffect, useState } from "react";
import { Pause, Play, Zap } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import ActiveOath from "@/components/live-feed/ActiveOath";
import DemoControls from "@/components/live-feed/DemoControls";
import EventRow from "@/components/live-feed/EventRow";
import { subscribeToEvents } from "@/lib/api";
import type { HorkosEvent } from "@/lib/types";

const MAX_EVENTS = 50;

export default function LiveFeedPage() {
  const [events, setEvents] = useState<HorkosEvent[]>([]);
  const [live, setLive] = useState(true);

  useEffect(() => {
    if (!live) return;
    const stop = subscribeToEvents((event) => {
      setEvents((list) => [event, ...list].slice(0, MAX_EVENTS));
    });
    return stop;
  }, [live]);

  return (
    <>
      <PageHeader
        title="Live Feed"
        subtitle="Everything Horkos does, as it happens."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="flex items-center gap-2 font-serif text-lg font-semibold sm:text-xl">
              <Zap size={18} className="text-accent" />
              Live Event Stream
            </h2>
            <div className="flex items-center gap-3 text-xs text-muted">
              <span className="font-mono">
                {events.length} event{events.length === 1 ? "" : "s"} •{" "}
                {live ? "Live updates on" : "Paused"}
              </span>
              <button
                type="button"
                onClick={() => setLive((v) => !v)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 font-medium text-foreground hover:bg-foreground/5"
              >
                {live ? <Pause size={13} /> : <Play size={13} />}
                {live ? "Pause" : "Resume"}
              </button>
            </div>
          </div>

          {events.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted">
              {live
                ? "Waiting for the next event…"
                : "Paused. Press Resume to see new events."}
            </div>
          ) : (
            <ol aria-live="polite" className="space-y-3">
              {events.map((e) => (
                <EventRow key={e.id} event={e} />
              ))}
            </ol>
          )}
        </section>

        <aside className="space-y-6 lg:sticky lg:top-6 lg:self-start">
          <DemoControls onReset={() => setEvents([])} />
          <ActiveOath />
        </aside>
      </div>
    </>
  );
}