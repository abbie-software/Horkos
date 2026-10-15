"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { navItems } from "@/lib/nav";
import { mockUser } from "@/lib/mock-data";
import ThemeToggle from "./ThemeToggle";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="min-h-screen">
      {/* Dark overlay behind the mobile menu */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-sidebar text-sidebar-foreground transition-transform duration-200 lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center justify-between px-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent font-serif text-lg font-semibold text-white">
              H
            </div>
            <div className="leading-tight">
              <p className="font-serif text-lg font-semibold text-white">
                Horkos
              </p>
              <p className="text-xs text-sidebar-muted">AI spending guard</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label="Close menu"
            className="rounded-lg p-2 text-sidebar-muted hover:bg-white/10 lg:hidden"
          >
            <X size={18} />
          </button>
        </div>

        <nav className="mt-4 flex-1 space-y-1 px-3">
          {navItems.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(item.href + "/");
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={`flex items-center gap-3 rounded-lg border-l-2 px-3 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? "border-accent bg-sidebar-active text-white"
                    : "border-transparent text-sidebar-muted hover:bg-sidebar-active/60 hover:text-white"
                }`}
              >
                <Icon size={18} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center justify-between border-t border-white/10 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-accent text-sm font-semibold text-white">
              {mockUser.name.charAt(0)}
            </div>
            <div className="leading-tight">
              <p className="text-sm font-medium text-white">{mockUser.name}</p>
              <p className="text-xs text-sidebar-muted">Buyer</p>
            </div>
          </div>
          <ThemeToggle variant="sidebar" />
        </div>
      </aside>

      {/* Content area */}
      <div className="lg:pl-64">
        {/* Top bar, mobile only */}
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-background/90 px-4 backdrop-blur lg:hidden">
          <button
            type="button"
            onClick={() => setOpen(true)}
            aria-label="Open menu"
            className="rounded-lg p-2 text-foreground hover:bg-foreground/5"
          >
            <Menu size={20} />
          </button>
          <p className="font-serif text-lg font-semibold">Horkos</p>
          <ThemeToggle />
        </header>

        <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-10 lg:py-10">
          {children}
        </main>
      </div>
    </div>
  );
}