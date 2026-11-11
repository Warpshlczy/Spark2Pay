import { Info } from 'lucide-react'
import type { Advice } from '../types'
import PayPalActionButton from './PayPalActionButton'
import { money } from '../lib/format'

interface Props {
  advice: Advice
  index: number
}

export default function AdviceCard({ advice, index }: Props) {
  const sym = advice.subscription?.currency_symbol ?? '$'
  const sub = advice.subscription

  return (
    <article className="panel panel-hover flex flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center">
      {/* Rank + identity */}
      <div className="flex min-w-0 flex-1 items-start gap-3.5">
        <span className="tnum mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center
                         rounded-md border border-hairline bg-ink-800 text-xs font-semibold
                         text-fog">
          {String(index + 1).padStart(2, '0')}
        </span>
        <div className="min-w-0">
          <h3 className="truncate text-[15px] font-semibold text-fog-bright">
            {advice.title}
          </h3>
          <p className="mt-1 text-[13px] leading-relaxed text-fog">
            {advice.rationale}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-fog-dim">
            {sub?.category && <span>{sub.category}</span>}
            {sub && <span className="tnum">{money(sub.price, sym)}/mo now</span>}
            <span className="tnum">
              confidence {Math.round(advice.confidence * 100)}%
            </span>
          </div>
        </div>
      </div>

      {/* Savings + execution */}
      <div className="flex shrink-0 items-center gap-4 sm:flex-col sm:items-end sm:gap-2">
        <div className="text-right">
          <p className="tnum text-lg font-semibold text-spark">
            −{money(advice.estimated_monthly_savings, sym)}
          </p>
          <p className="text-[10px] font-medium uppercase tracking-wider text-fog-dim">
            saved / month
          </p>
        </div>

        {advice.action_available ? (
          <PayPalActionButton
            subscriptionId={advice.subscription_id}
            actionType={advice.recommended_action === 'cancel' ? 'cancel'
                        : advice.recommended_action === 'optimize' ? 'cancel'
                        : advice.recommended_action}
            reason={advice.title}
          />
        ) : (
          <div className="flex max-w-[190px] items-start gap-2 rounded-lg
                          border border-hairline bg-ink-800 px-3 py-2">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-fog-dim" />
            <p className="text-[11px] leading-snug text-fog">
              Billed by card — cancel manually on the merchant site.
            </p>
          </div>
        )}
      </div>
    </article>
  )
}
