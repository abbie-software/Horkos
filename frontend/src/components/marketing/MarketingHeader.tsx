import Link from "next/link";
import { Mark } from "@/components/brand/Logo";
import ThemeToggle from "@/components/ThemeToggle";

export default function MarketingHeader() {
  return (
    <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
      <Link href="/" className="flex items-center gap-3">
        <Mark className="h-9 w-9" />
        <span className="font-serif text-xl font-semibold tracking-wide">Horkos</span>
      </Link>
      <nav className="flex items-center gap-5 text-sm font-medium">
        <Link href="/about">About</Link>
        <ThemeToggle />
        <Link
          href="/money-tracker"
          className="rounded-full bg-brand px-5 py-2 font-semibold text-brand-foreground active:scale-[0.97]"
        >
          Open app
        </Link>
      </nav>
    </header>
  );
}