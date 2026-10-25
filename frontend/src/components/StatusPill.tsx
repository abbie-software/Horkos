import { Clock } from "lucide-react";
import { statusMeta, toneClasses } from "@/lib/payment-ui";
import type { PaymentStatus } from "@/lib/types";

export default function StatusPill({ status }: { status: PaymentStatus }) {
  // If the server sends a status we don't know, show it plainly instead of crashing
  const meta = statusMeta[status] ?? {
    label: String(status).replace(/_/g, " "),
    tone: "neutral" as const,
    icon: Clock,
  };
  const Icon = meta.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1 text-xs font-semibold ${toneClasses[meta.tone]}`}
    >
      <Icon size={14} />
      {meta.label}
    </span>
  );
}