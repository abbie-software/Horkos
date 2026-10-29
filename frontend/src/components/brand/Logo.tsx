"use client";

import { motion } from "motion/react";
import { LOGO_PATHS, LOGO_VIEWBOX, MARK_VIEWBOX } from "./logo-paths";

const EASE = [0.23, 1, 0.32, 1] as const;
const COLOR = { brand: "var(--brand)", gold: "var(--accent)" };

export function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox={LOGO_VIEWBOX} role="img" aria-label="Horkos" className={className}>
      {LOGO_PATHS.map((p, i) => (
        <motion.path
          key={i}
          d={p.d}
          fillRule="evenodd"
          fill={COLOR[p.color]}
          stroke={COLOR[p.color]}
          strokeWidth={3}
          strokeLinejoin="round"
          initial={{ pathLength: 0, fillOpacity: 0 }}
          animate={{ pathLength: 1, fillOpacity: 1 }}
          transition={{
            pathLength: { delay: p.delay, duration: p.dur, ease: EASE },
            fillOpacity: { delay: p.delay + p.dur * 0.75, duration: 0.5 },
          }}
        />
      ))}
    </svg>
  );
}

export function Mark({
  className,
  fill = "var(--brand)",
}: {
  className?: string;
  fill?: string;
}) {
  return (
    <svg viewBox={MARK_VIEWBOX} role="img" aria-label="Horkos" className={className}>
      {LOGO_PATHS.filter((p) => p.group === "mark").map((p, i) => (
        <path key={i} d={p.d} fill={fill} fillRule="evenodd" />
      ))}
    </svg>
  );
}