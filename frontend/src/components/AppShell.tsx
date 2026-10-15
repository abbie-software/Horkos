"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

export default function ThemeToggle({
  variant = "default",
}: {
  variant?: "default" | "sidebar";
}) {
  const [dark, setDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
    setMounted(true);
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("horkos-theme", next ? "dark" : "light");
    } catch {}
  }

  const styles =
    variant === "sidebar"
      ? "border-white/15 text-sidebar-foreground hover:bg-white/10"
      : "border-border text-foreground hover:bg-foreground/5";

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      className={`inline-flex h-9 w-9 items-center justify-center rounded-lg border transition-colors ${styles}`}
    >
      {mounted ? dark ? <Sun size={18} /> : <Moon size={18} /> : null}
    </button>
  );
}