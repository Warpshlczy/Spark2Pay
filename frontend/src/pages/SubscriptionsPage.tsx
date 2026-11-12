import { useEffect, useState } from 'react'
import { Loader2, Zap, CreditCard, CircleSlash, CheckCircle2 } from 'lucide-react'
import { api } from '../lib/api'
import type { Subscription } from '../types'
import { money, monthlyCost, cycleName, shortDate } from '../lib/format'
import PayPalActionButton from '../components/PayPalActionButton'

export default function SubscriptionsPage() {
  const [subs, setSubs] = useState<Subscription[] | null>(null)
  const [showInactive, setShowInactive] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    // fetch everything; the "Show cancelled" toggle filters client-side
    api.get<{ data: Subscription[] }>('/subscriptions?inactive=true')
      .then(r => setSubs(r.data))
      .catch(exc => setError(exc instanceof Error ? exc.message : 'Load failed'))
  }

  useEffect(load, [])

  if (!subs && !error) {
    return (
      <div className="flex h-[60vh] items-center justify-center gap-3 text-fog">
        <Loader2 className="h-5 w-5 spinner" />
        <span className="text-sm">Loading subscriptions…</span>
      </div>
    )
  }

  const visible = (subs ?? []).filter(s => showInactive || !s.inactive)
  const activeCount = (subs ?? []).filter(s => !s.inactive).length

  return (
    <div>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-[26px] font-bold tracking-tight text-fog-bright">
            Subscriptions
          </h1>
          <p className="mt-1 text-sm text-fog">
            {activeCount} active · one-click execution for linked subscriptions
          </p>
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-xs text-fog">
          <input type="checkbox" checked={showInactive}
                 onChange={e => setShowInactive(e.target.checked)}
                 className="h-3.5 w-3.5 accent-[#2E7CFF]" />
          Show cancelled
        </label>
      </header>

      {error && (
        <p className="panel mb-6 border-coral/30 px-4 py-3 text-xs text-coral">{error}</p>
      )}

      <div className="panel divide-y divide-hairline overflow-hidden">
        {visible.map(s => (
          <SubRow key={s.id} sub={s} onChanged={load} />
        ))}
        {visible.length === 0 && (
          <p className="px-5 py-8 text-center text-sm text-fog">
            Nothing here yet.
          </p>
        )}
      </div>
    </div>
  )
}

function SubRow({ sub, onChanged }: { sub: Subscription; onChanged: () => void }) {
  const sym = sub.currency?.symbol ?? '$'
  const monthly = monthlyCost(sub.price, sub.cycle, sub.frequency)

  return (
    <div className={`flex flex-wrap items-center gap-4 px-5 py-4
                     transition-colors hover:bg-ink-800/40 ${sub.inactive ? 'opacity-55' : ''}`}>
      {/* Identity */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h3 className="truncate text-[15px] font-semibold text-fog-bright">
            {sub.name}
          </h3>
          {sub.inactive
            ? <span className="inline-flex items-center gap-1 rounded-full border
                               border-hairline bg-ink-700 px-2 py-0.5 text-[10px]
                               font-semibold text-fog">
                <CircleSlash className="h-3 w-3" /> cancelled
              </span>
            : sub.paypal_subscription_id
              ? <span className="inline-flex items-center gap-1 rounded-full border
                                 border-bolt/30 bg-bolt-dim/40 px-2 py-0.5 text-[10px]
                                 font-semibold text-bolt-soft">
                  <Zap className="h-3 w-3" fill="currentColor" /> one-click
                </span>
              : <span className="inline-flex items-center gap-1 rounded-full border
                                 border-hairline px-2 py-0.5 text-[10px] font-semibold
                                 text-fog">
                  <CreditCard className="h-3 w-3" /> card
                </span>}
        </div>
        <p className="tnum mt-1 text-[11px] text-fog-dim">
          {cycleName(sub.cycle, sub.frequency)} · next {shortDate(sub.next_payment)}
          {sub.category ? ` · ${sub.category.name}` : ''}
        </p>
      </div>

      {/* Money */}
      <div className="text-right">
        <p className="tnum text-[15px] font-semibold text-fog-bright">
          {money(sub.price, sym)}
        </p>
        <p className="tnum text-[11px] text-fog-dim">
          {money(Math.round(monthly * 100) / 100, sym)}/mo
        </p>
      </div>

      {/* Execution */}
      {!sub.inactive && sub.paypal_subscription_id && (
        <PayPalActionButton
          subscriptionId={sub.id}
          actionType="cancel"
          reason={`Manual cancellation from Subscriptions page`}
          label="One-click cancel"
          onDone={onChanged}
          className="w-full sm:w-auto"
        />
      )}
      {!sub.inactive && !sub.paypal_subscription_id && (
        <span className="inline-flex items-center gap-1.5 text-[11px] text-fog-dim">
          <CheckCircle2 className="h-3.5 w-3.5" /> cancel on merchant site
        </span>
      )}
    </div>
  )
}
