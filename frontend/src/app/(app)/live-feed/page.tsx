"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Pause, Play, RotateCcw, Zap } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import ActiveOath from "@/components/live-feed/ActiveOath";
import DemoControls from "@/components/live-feed/DemoControls";
import EventRow from "@/components/live-feed/EventRow";
import { restartMockEvents, subscribeToEvents } from "@/lib/api";
import type { HorkosEvent } from "@/lib/types";

const MAX_EVENTS = 10;

export default function LiveFeedPage() {
  const [events, setEvents] = useState<HorkosEvent[]>([]);
  const [live, setLive] = useState(true);
  const [finished, setFinished] = useState(false);
  const [run, setRun] = useState(0);

  // Each visit to the page starts the demo story from the beginning.
  // This must stay ABOVE the subscribe effect.
  useEffect(() => {
    restartMockEvents();
  }, []);

  useEffect(() => {
    if (!live) return;
    const stop = subscribeToEvents(
      (event) => {
        setEvents((list) =>
          list.some((e) => e.id === event.id)
            ? list
            : [event, ...list].slice(0, MAX_EVENTS)
        );
      },
      () => setFinished(true)
    );
    return stop;
  }, [live, run]);

  function restart() {
    restartMockEvents();
    setEvents([]);
    setFinished(false);
    setRun((n) => n + 1);
  }

  function togglePause() {
    setLive((v) => !v);
  }

  const status = finished ? "Story finished" : live ? "Live updates on" : "Paused";

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
                {events.length} event{events.length === 1 ? "" : "s"} • {status}
              </span>
              {finished ? (
                <button
                  type="button"
                  onClick={restart}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 font-medium text-foreground hover:bg-foreground/5"
                >
                  <RotateCcw size={13} />
                  Replay
                </button>
              ) : (
                <button
                  type="button"
                  onClick={togglePause}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 font-medium text-foreground hover:bg-foreground/5"
                >
                  {live ? <Pause size={13} /> : <Play size={13} />}
                  {live ? "Pause" : "Resume"}
                </button>
              )}
            </div>
          </div>

          {events.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted">
              {live
                ? "Waiting for the next event…"
                : "Paused. Press Resume to see new events."}
            </div>
          ) : (
            <ol
              aria-live="polite"
              className="max-h-[70vh] space-y-3 overflow-y-auto pr-1"
            >
              {events.map((e) => (
                <EventRow key={e.id} event={e} />
              ))}
            </ol>
          )}

          {events.length >= MAX_EVENTS && (
            <p className="mt-3 text-xs text-muted">
              Showing the latest {MAX_EVENTS} events. Older ones are in the{" "}
              <Link href="/audit-trail" className="font-semibold underline">
                Audit Trail
              </Link>
              .
            </p>
          )}
        </section>

        <aside className="space-y-6 lg:sticky lg:top-6 lg:self-start">
          <DemoControls onReset={restart} />
          <ActiveOath />
        </aside>
      </div>
    </>
  );
}