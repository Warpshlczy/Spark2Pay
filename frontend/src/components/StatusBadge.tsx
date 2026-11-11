import { CheckCircle2, XCircle, Clock, Loader2, MinusCircle } from 'lucide-react'
import type { PayPalAction } from '../types'

const MAP: Record<PayPalAction['status'],
  { label: string; cls: string; icon: React.ReactNode }> = {
  completed: {
    label: 'Completed',
    cls: 'bg-mint-dim text-mint border-mint/30',
    icon: <CheckCircle2 className="h-3.5 w-3.5" />
  },
  pending_approval: {
    label: 'Pending approval',
    cls: 'bg-spark-dim text-spark border-spark/30',
    icon: <Clock className="h-3.5 w-3.5" />
  },
  executing: {
    label: 'Executing',
    cls: 'bg-bolt-dim/60 text-bolt-soft border-bolt/30',
    icon: <Loader2 className="h-3.5 w-3.5 spinner" />
  },
  failed: {
    label: 'Failed',
    cls: 'bg-coral-dim text-coral border-coral/30',
    icon: <XCircle className="h-3.5 w-3.5" />
  },
  rejected: {
    label: 'Rejected',
    cls: 'bg-ink-700 text-fog border-hairline',
    icon: <MinusCircle className="h-3.5 w-3.5" />
  }
}

export default function StatusBadge({ status }: { status: PayPalAction['status'] }) {
  const cfg = MAP[status] ?? MAP.rejected
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1
                      text-[11px] font-semibold ${cfg.cls}`}>
      {cfg.icon}
      {cfg.label}
    </span>
  )
}
