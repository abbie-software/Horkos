"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Logo } from "@/components/brand/Logo";

const EASE = [0.23, 1, 0.32, 1] as const;

export default function Intro({ onDone }: { onDone: () => void }) {
  const reduce = useReducedMotion();
  const [show, setShow] = useState(true);

  const finish = useCallback(() => {
    setShow(false);
  }, []);

  useEffect(() => {
    if (reduce) {
      onDone();
      return;
    }
    const timer = setTimeout(finish, 3600);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && finish();
    window.addEventListener("keydown", onKey);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("keydown", onKey);
    };
  }, [reduce, onDone, finish]);

  return (
    <AnimatePresence onExitComplete={onDone}>
      {show && !reduce && (
        <motion.div
          key="intro"
          onClick={finish}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-background px-6"
          exit={{ opacity: 0, scale: 1.03, transition: { duration: 0.55, ease: EASE } }}
        >
          <Logo className="w-full max-w-3xl" />
        </motion.div>
      )}
    </AnimatePresence>
  );
}