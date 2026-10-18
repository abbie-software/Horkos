import { statusMeta, toneClasses } from "@/lib/payment-ui";
import type { PaymentStatus } from "@/lib/types";

export default function StatusPill({ status }: { status: PaymentStatus }) {
  const meta = statusMeta[status];
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