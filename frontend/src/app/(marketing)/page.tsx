"use client";

import { useCallback, useRef, useState } from "react";
import Link from "next/link";
import { motion, useScroll, useTransform, type MotionValue } from "motion/react";
import { Mark } from "@/components/brand/Logo";
import Intro from "@/components/marketing/Intro";
import MarketingHeader from "@/components/marketing/MarketingHeader";

const EASE = [0.23, 1, 0.32, 1] as const;
const PRIMARY =
  "inline-flex items-center rounded-full bg-brand px-7 py-3.5 text-sm font-semibold text-brand-foreground transition-transform duration-150 ease-out active:scale-[0.97]";

const STEPS = [
  { title: "You write the oath.", text: "In plain English: how much, for what, and when to ask you first. Horkos turns it into rules." },
  { title: "The Guard checks every payment.", text: "Fixed rules come first and no AI can override them. Risky payments are blocked. Unsure ones come to you." },
  { title: "Money waits until the work is proven.", text: "Tests run on what the seller delivers. Pass, and they are paid. Fail, and you are refunded." },
  { title: "Trust is earned.", text: "New sellers start with small limits. Clean deliveries raise them. A failure tightens them at once." },
];

function Step({ i, progress, title, text }: { i: number; progress: MotionValue<number>; title: string; text: string }) {
  const n = STEPS.length;
  const a = i / n;
  const b = (i + 1) / n;
  const last = i === n - 1;
  const opacity = useTransform(
    progress,
    last ? [a - 0.08, a, 1, 1.01] : [a - 0.08, a, b - 0.02, b + 0.06],
    last ? [0.22, 1, 1, 1] : [0.22, 1, 1, 0.22]
  );
  return (
    <motion.li style={{ opacity }} className="flex gap-5">
      <span className="font-serif text-3xl text-accent sm:text-4xl">{i + 1}</span>
      <div>
        <h3 className="font-serif text-2xl sm:text-4xl">{title}</h3>
        <p className="mt-2 max-w-md text-sm text-muted sm:text-base">{text}</p>
      </div>
    </motion.li>
  );
}

export default function Landing() {
  const [ready, setReady] = useState(false);
  const done = useCallback(() => setReady(true), []);
  const storyRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: storyRef, offset: ["start start", "end end"] });
  const lines = ["Agents can spend.", "Horkos holds them", "to their word."];
  const fade = (delay: number) => ({
    initial: { opacity: 0, y: 12 },
    animate: ready ? { opacity: 1, y: 0 } : undefined,
    transition: { duration: 0.6, ease: EASE, delay },
  });

  return (
    <>
      <Intro onDone={done} />
      <MarketingHeader />
      <main>
        <section className="mx-auto flex min-h-[86vh] max-w-6xl flex-col justify-center px-6 pb-16 pt-8">
          <h1 className="font-serif text-[2.75rem] leading-[0.98] tracking-tight sm:text-7xl lg:text-[6.5rem]">
            {lines.map((line, i) => (
              <span key={line} className="block overflow-hidden pb-2">
                <motion.span
                  className={`block ${i === 2 ? "text-brand" : ""}`}
                  initial={{ y: "110%" }}
                  animate={{ y: ready ? 0 : "110%" }}
                  transition={{ duration: 0.9, ease: EASE, delay: i * 0.09 }}
                >
                  {line}
                </motion.span>
              </span>
            ))}
          </h1>
          <motion.p {...fade(0.4)} className="mt-8 max-w-xl text-lg text-muted">
            An AI guard that enforces your spending rules, holds payments until
            work is proven, and gives more freedom to sellers who earn trust.
          </motion.p>
          <motion.div {...fade(0.5)} className="mt-10 flex flex-wrap items-center gap-6">
            <Link href="/money-tracker" className={PRIMARY}>Open Horkos</Link>
            <a href="#oath" className="text-sm font-semibold underline underline-offset-4">See how it works</a>
          </motion.div>
        </section>

        <section id="oath" ref={storyRef} className="relative h-[300vh]">
          <div className="sticky top-0 flex h-screen items-center">
            <div className="mx-auto grid w-full max-w-6xl items-center gap-8 px-6 lg:grid-cols-2 lg:gap-16">
              <div className="relative mx-auto aspect-square w-40 sm:w-64 lg:w-96">
                <svg viewBox="0 0 100 100" className="absolute inset-0 -rotate-90" aria-hidden="true">
                  <circle cx="50" cy="50" r="48" fill="none" stroke="var(--border)" strokeWidth="0.8" />
                  <motion.circle cx="50" cy="50" r="48" fill="none" stroke="var(--brand)" strokeWidth="1.4" strokeLinecap="round" style={{ pathLength: scrollYProgress }} />
                </svg>
                <Mark className="absolute inset-[18%] h-[64%] w-[64%]" />
              </div>
              <ol className="space-y-6 sm:space-y-10">
                {STEPS.map((s, i) => (
                  <Step key={s.title} i={i} progress={scrollYProgress} title={s.title} text={s.text} />
                ))}
              </ol>
            </div>
          </div>
        </section>

        <section className="mx-auto flex min-h-[70vh] max-w-6xl flex-col items-start justify-center px-6">
          <h2 className="font-serif text-5xl leading-none tracking-tight sm:text-7xl">Hold them to their word.</h2>
          <Link href="/money-tracker" className={`${PRIMARY} mt-10`}>Open Horkos</Link>
        </section>
      </main>

      <footer className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 border-t border-border px-6 py-8 text-sm text-muted">
        <p>Runs on the PayPal sandbox. No real money moves.</p>
        <Link href="/about" className="underline underline-offset-4">About</Link>
      </footer>
    </>
  );
}