import Link from "next/link";
import { Mark } from "@/components/brand/Logo";
import ThemeToggle from "@/components/ThemeToggle";

export default function SellerLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4 sm:px-6">
        <Link href="/" className="flex items-center gap-3">
          <Mark className="h-8 w-8" />
          <span className="font-serif text-lg font-semibold tracking-wide">
            Horkos <span className="font-normal text-muted">for sellers</span>
          </span>
        </Link>
        <nav className="flex items-center gap-4 text-sm font-medium">
          <Link href="/money-tracker">Buyer app</Link>
          <ThemeToggle />
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 pb-16 pt-4 sm:px-6">{children}</main>
    </div>
  );
}