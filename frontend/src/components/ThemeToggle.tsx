"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";

function subscribeToTheme(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
  });
  return () => observer.disconnect();
}

function getThemeSnapshot() {
  return document.documentElement.classList.contains("dark");
}

function getServerThemeSnapshot() {
  return false;
}

export default function ThemeToggle({
  variant = "default",
}: {
  variant?: "default" | "sidebar";
}) {
  const dark = useSyncExternalStore(
    subscribeToTheme,
    getThemeSnapshot,
    getServerThemeSnapshot
  );

  function toggle() {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("horkos-theme", next ? "dark" : "light");
    } catch {}
  }

  const styles =
    variant === "sidebar"
      ? "border-sidebar-active text-sidebar-foreground hover:bg-sidebar-active"
      : "border-border text-foreground hover:bg-foreground/5";

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      className={`inline-flex h-9 w-9 items-center justify-center rounded-lg border transition-colors ${styles}`}
    >
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}