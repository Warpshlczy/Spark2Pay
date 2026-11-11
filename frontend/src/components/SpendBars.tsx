import { money, monthlyCost } from '../lib/format'
import type { Subscription } from '../types'

/** Category spend breakdown - real data, mono numerals, no chart library. */
export default function SpendBars({ subscriptions }: { subscriptions: Subscription[] }) {
  const active = subscriptions.filter(s => !s.inactive)

  const byCategory = new Map<string, number>()
  for (const s of active) {
    const key = s.category?.name ?? 'Uncategorized'
    byCategory.set(key, (byCategory.get(key) ?? 0) +
      monthlyCost(s.price, s.cycle, s.frequency))
  }

  const rows = [...byCategory.entries()]
    .map(([name, value]) => ({ name, value: Math.round(value * 100) / 100 }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6)

  const max = Math.max(...rows.map(r => r.value), 1)

  return (
    <section className="panel px-5 py-4">
      <h2 className="text-sm font-semibold text-fog-bright">Where the money goes</h2>
      <p className="mt-0.5 text-xs text-fog-dim">Monthly-equivalent spend by category</p>

      <div className="mt-4 flex flex-col gap-3">
        {rows.map(r => (
          <div key={r.name} className="flex items-center gap-3">
            <span className="w-24 shrink-0 truncate text-xs text-fog">{r.name}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-700">
              <div className="h-full rounded-full bg-bolt transition-all duration-500"
                   style={{ width: `${(r.value / max) * 100}%` }} />
            </div>
            <span className="tnum w-16 shrink-0 text-right text-xs font-medium text-fog-bright">
              {money(r.value)}
            </span>
          </div>
        ))}
        {rows.length === 0 && (
          <p className="text-xs text-fog-dim">No active subscriptions yet.</p>
        )}
      </div>
    </section>
  )
}
