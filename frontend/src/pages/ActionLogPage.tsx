import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { api } from '../lib/api'
import type { PayPalAction } from '../types'
import StatusBadge from '../components/StatusBadge'
import { money, dateTime } from '../lib/format'

export default function ActionLogPage() {
  const [actions, setActions] = useState<PayPalAction[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<{ data: PayPalAction[] }>('/paypal/actions')
      .then(r => setActions(r.data))
      .catch(exc => setError(exc instanceof Error ? exc.message : 'Load failed'))
  }, [])

  return (
    <div>
      <header className="mb-6">
        <h1 className="font-display text-[26px] font-bold tracking-tight text-fog-bright">
          Action Log
        </h1>
        <p className="mt-1 text-sm text-fog">
          Every PayPal execution attempt, with its full audit trail
        </p>
      </header>

      {error && (
        <p className="panel mb-6 border-coral/30 px-4 py-3 text-xs text-coral">{error}</p>
      )}

      {!actions && !error && (
        <div className="flex h-[50vh] items-center justify-center gap-3 text-fog">
          <Loader2 className="h-5 w-5 spinner" />
          <span className="text-sm">Loading audit trail…</span>
        </div>
      )}

      {actions && (
        <div className="panel overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-[13px]">
            <thead>
              <tr className="border-b border-hairline text-[11px] uppercase
                             tracking-wider text-fog-dim">
                <th className="px-5 py-3 font-semibold">When</th>
                <th className="px-5 py-3 font-semibold">Subscription</th>
                <th className="px-5 py-3 font-semibold">Action</th>
                <th className="px-5 py-3 font-semibold">Status</th>
                <th className="px-5 py-3 text-right font-semibold">Amount</th>
                <th className="px-5 py-3 text-right font-semibold">Saved /mo</th>
                <th className="px-5 py-3 font-semibold">PayPal ref</th>
                <th className="px-5 py-3 font-semibold">Mode</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline">
              {actions.map(a => (
                <tr key={a.id} className="transition-colors hover:bg-ink-800/40">
                  <td className="tnum px-5 py-3 text-fog">
                    {dateTime(a.executed_at ?? a.created_at)}
                  </td>
                  <td className="px-5 py-3 font-medium text-fog-bright">
                    {a.subscription_name ?? `#${a.subscription_id ?? '—'}`}
                  </td>
                  <td className="px-5 py-3">
                    <span className="rounded border border-hairline bg-ink-800 px-2 py-0.5
                                     text-[11px] font-semibold uppercase tracking-wide
                                     text-fog">
                      {a.action_type}
                    </span>
                  </td>
                  <td className="px-5 py-3"><StatusBadge status={a.status} /></td>
                  <td className="tnum px-5 py-3 text-right text-fog">
                    {a.amount !== null ? money(a.amount, a.currency === 'USD' ? '$' : '') : '—'}
                  </td>
                  <td className="tnum px-5 py-3 text-right font-semibold text-spark">
                    {a.estimated_monthly_savings !== null
                      ? `−${money(a.estimated_monthly_savings)}` : '—'}
                  </td>
                  <td className="tnum px-5 py-3 text-[11px] text-fog-dim">
                    {a.paypal_order_id ?? a.paypal_subscription_id ?? '—'}
                    {a.paypal_capture_id && (
                      <span className="block">cap: {a.paypal_capture_id}</span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <span className={`tnum rounded border px-2 py-0.5 text-[10px]
                                      font-semibold ${
                      a.paypal_mode === 'sandbox'
                        ? 'border-bolt/30 bg-bolt-dim/40 text-bolt-soft'
                        : 'border-hairline bg-ink-800 text-fog'}`}>
                      {a.paypal_mode}
                    </span>
                    {a.error && (
                      <span className="mt-1 block max-w-[220px] text-[10px]
                                       leading-snug text-coral">{a.error}</span>
                    )}
                  </td>
                </tr>
              ))}
              {actions.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-5 py-10 text-center text-sm text-fog">
                    No PayPal actions yet. Accept an AI recommendation on the
                    Dashboard to create your first audited execution.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
