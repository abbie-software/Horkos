import {
  Activity,
  ClipboardList,
  ScrollText,
  ShieldCheck,
  Wallet,
} from "lucide-react";

export const navItems = [
  { href: "/oath", label: "Oath", icon: ScrollText },
  { href: "/live-feed", label: "Live Feed", icon: Activity },
  { href: "/money-tracker", label: "Money Tracker", icon: Wallet },
  { href: "/trust-board", label: "Trust Board", icon: ShieldCheck },
  { href: "/audit-trail", label: "Audit Trail", icon: ClipboardList },
];