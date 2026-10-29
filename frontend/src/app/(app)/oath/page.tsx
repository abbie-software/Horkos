"use client";

import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import OathEditor from "@/components/oath/OathEditor";
import PolicySummary from "@/components/oath/PolicySummary";
import { ApiRequestError, getOath, saveOath } from "@/lib/api";
import type { Oath } from "@/lib/types";

function errorText(e: unknown) {
  return e instanceof Error ? e.message : "Something went wrong. Please try again.";
}

export default function OathPage() {
  const [oath, setOath] = useState<Oath | null>(null);
  const [noOath, setNoOath] = useState(false);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getOath()
      .then((o) => {
        if (cancelled) return;
        setOath(o);
        setText(o.raw_text);
      })
      .catch((e) => {
        if (cancelled) return;
        if (e instanceof ApiRequestError && e.status === 404) {
          setNoOath(true); // nothing saved yet: start with an empty box
        } else {
          setError(errorText(e));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const dirty = oath
    ? text.trim() !== oath.raw_text.trim()
    : text.trim().length > 0;

  async function handleSave() {
    setSaving(true);
    setError(null);
    setNote(null);
    try {
      const updated = await saveOath(text.trim());
      setOath(updated);
      setNoOath(false);
      setText(updated.raw_text);
      setNote("Oath saved.");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setSaving(false);
    }
  }

  function handleReset() {
    setText(oath ? oath.raw_text : "");
    setError(null);
    setNote(null);
  }

  return (
    <>
      <PageHeader
        title="Your Oath"
        subtitle="Write your spending rules in plain English. Horkos enforces them on every payment."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <OathEditor
          text={text}
          loading={loading}
          saving={saving}
          dirty={dirty}
          note={note ?? (noOath ? "No oath saved yet" : null)}
          error={error}
          onChange={(value) => {
            setText(value);
            setNote(null);
          }}
          onSave={handleSave}
          onReset={handleReset}
        />
        <PolicySummary
          policy={oath ? oath.policy : null}
          dirty={dirty}
          empty={noOath}
        />
      </div>

      <div className="mt-6 flex items-start gap-3 rounded-xl border-l-4 border-accent bg-card p-4">
        <ShieldCheck size={20} className="mt-0.5 shrink-0 text-accent" />
        <p className="text-sm">
          <span className="font-serif text-base font-semibold">
            Hard rules beat AI.{" "}
          </span>
          <span className="text-muted">
            Your caps and blocks are fixed rules. The AI cannot override them.
          </span>
        </p>
      </div>
    </>
  );
}