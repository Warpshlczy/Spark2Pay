import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, Wallet, Repeat, PiggyBank, Loader2, RefreshCw,
         Bot, Cpu } from 'lucide-react'
import { api } from '../lib/api'
import type { AdviceResponse, Subscription } from '../types'
import SparkStatCard, { useCountUp } from '../components/SparkStatCard'
import AdviceCard from '../components/AdviceCard'
import SpendBars from '../components/SpendBars'
import { money, monthlyCost, shortDate, daysUntil } from '../lib/format'

export default function DashboardPage() {
  const [advice, setAdvice] = useState<AdviceResponse | null>(null)
  const [subs, setSubs] = useState<Subscription[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [regenerating, setRegenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (regen = false) => {
    regen ? setRegenerating(true) : setLoading(true)
    setError(null)
    try {
      const [adviceResp, subsResp] = await Promise.all([
        api.get<{ data: AdviceResponse }>('/ai/recommendations'),
        api.get<{ data: Subscription[] }>('/subscriptions')
      ])
      setAdvice(adviceResp.data)
      setSubs(subsResp.data)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Failed to load dashboard')
    } finally {
      setLoading(false)
      setRegenerating(false)
    }
  }, [])

  useEffect(() => { load(false) }, [load])

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center gap-3 text-fog">
        <Loader2 className="h-5 w-5 spinner" />
        <span className="text-sm">Reading your subscriptions…</span>
      </div>
    )
  }

  return (
    <div>
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-[26px] font-bold tracking-tight text-fog-bright">
            Dashboard
          </h1>
          <p className="mt-1 flex items-center gap-2 text-sm text-fog">
            {advice?.engine === 'openai'
              ? <><Bot className="h-4 w-4 text-bolt-soft" />
                  LLM agent analyzed your portfolio via function calling</>
              : <><Cpu className="h-4 w-4 text-bolt-soft" />
                  Rules engine analyzed your portfolio</>}
            {advice?.note && (
              <span className="tnum rounded border border-hairline px-1.5 py-0.5
                               text-[10px] text-fog-dim">{advice.note}</span>
            )}
          </p>
        </div>
        <button onClick={() => load(true)} disabled={regenerating} className="btn-ghost">
          <RefreshCw className={`h-4 w-4 ${regenerating ? 'spinner' : ''}`} />
          Re-run AI analysis
        </button>
      </header>

      {error && (
        <p className="panel mb-6 border-coral/30 px-4 py-3 text-xs text-coral">{error}</p>
      )}

      {subs && <StatRow subs={subs} advice={advice} />}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        {/* AI advice feed - the heart of the product */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-fog-bright">AI savings advice</h2>
            {advice && advice.advice.length > 0 && (
              <span className="tnum rounded-full border border-spark/30 bg-spark-dim
                               px-2.5 py-0.5 text-[11px] font-semibold text-spark">
                {advice.advice.length} opportunities
              </span>
            )}
          </div>

          <div className="flex flex-col gap-3">
            {advice?.advice.map((a, i) => (
              <AdviceCard key={`${a.subscription_id}-${i}`} advice={a} index={i} />
            ))}
            {advice && advice.advice.length === 0 && (
              <div className="panel px-5 py-8 text-center">
                <p className="text-sm text-fog">No waste detected. You are lean.</p>
              </div>
            )}
          </div>
        </section>

        {/* Right rail */}
        <div className="flex flex-col gap-6">
          {subs && <SpendBars subscriptions={subs} />}
          {subs && <Upcoming subs={subs} />}
        </div>
      </div>
    </div>
  )
}

function StatRow({ subs, advice }: {
  subs: Subscription[]; advice: AdviceResponse | null
}) {
  const active = subs.filter(s => !s.inactive)
  const monthly = active.reduce(
    (sum, s) => sum + monthlyCost(s.price, s.cycle, s.frequency), 0)
  const savings = (advice?.advice ?? [])
    .reduce((sum, a) => sum + a.estimated_monthly_savings, 0)
  const counted = useCountUp(savings)

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <SparkStatCard label="Monthly spend" icon={<Wallet className="h-4 w-4" />}
                     value={money(monthly)}
                     sub={`${active.length} active subscriptions`} />
      <SparkStatCard label="Active" icon={<Repeat className="h-4 w-4" />}
                     value={String(active.length)}
                     sub={`${subs.length - active.length} already cancelled`} />
      <SparkStatCard label="AI-found savings" tone="spark"
                     icon={<PiggyBank className="h-4 w-4" />}
                     value={money(counted)}
                     sub={advice?.summary ?? 'No analysis yet'}
                     pulse={savings > 0} />
      <SparkStatCard label="PayPal layer" icon={<Sparkles className="h-4 w-4" />}
                     value={advice?.paypal_mode === 'sandbox' ? 'Sandbox' : 'Simulation'}
                     sub={advice?.paypal_mode === 'sandbox'
                          ? 'Executing against real PayPal sandbox'
                          : 'Deterministic local execution demo'} />
    </div>
  )
}

function Upcoming({ subs }: { subs: Subscription[] }) {
  const active = subs
    .filter(s => !s.inactive && s.next_payment)
    .sort((a, b) => (a.next_payment! < b.next_payment! ? -1 : 1))
    .slice(0, 5)

  return (
    <section className="panel px-5 py-4">
      <h2 className="text-sm font-semibold text-fog-bright">Next renewals</h2>
      <div className="mt-3 flex flex-col divide-y divide-hairline">
        {active.map(s => {
          const days = daysUntil(s.next_payment)
          return (
            <div key={s.id} className="flex items-center justify-between py-2.5">
              <div className="min-w-0">
                <p className="truncate text-[13px] font-medium text-fog-bright">
                  {s.name}
                </p>
                <p className="text-[11px] text-fog-dim">
                  {shortDate(s.next_payment)}
                </p>
              </div>
              <div className="text-right">
                <p className="tnum text-[13px] font-semibold text-fog-bright">
                  {money(s.price, s.currency?.symbol ?? '$')}
                </p>
                <p className={`text-[11px] ${days !== null && days <= 3
                                         ? 'text-spark' : 'text-fog-dim'}`}>
                  {days !== null ? (days === 0 ? 'today' : `in ${days}d`) : '—'}
                </p>
              </div>
            </div>
          )
        })}
        {active.length === 0 && (
          <p className="py-2 text-xs text-fog-dim">Nothing scheduled.</p>
        )}
      </div>
      <Link to="/subscriptions"
            className="mt-3 text-xs font-medium text-bolt-soft hover:text-bolt">
        View all subscriptions →
      </Link>
    </section>
  )
}
