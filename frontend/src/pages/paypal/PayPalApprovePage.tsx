/**
 * The approval confirmation step for manage-subscription actions
 * (cancel / suspend / activate). PayPal's Subscriptions API has no hosted
 * approval screen, so Spark2Pay provides this human-in-the-loop gate:
 * the AI proposed, the user must click "Approve" before anything executes.
 */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Zap, CheckCircle2, XCircle, Loader2, ArrowLeft, ShieldCheck } from 'lucide-react'
import { api, ApiError } from '../../lib/api'
import type { PayPalAction } from '../../types'
import { money, dateTime } from '../../lib/format'
import { useCountUp } from '../../components/SparkStatCard'

type Phase = 'loading' | 'confirm' | 'executing' | 'done' | 'failed' | 'gone'

export default function PayPalApprovePage() {
  const { actionId } = useParams()
  const [phase, setPhase] = useState<Phase>('loading')
  const [action, setAction] = useState<PayPalAction | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<{ data: PayPalAction }>(`/paypal/actions/${actionId}`)
      .then(r => {
        setAction(r.data)
        setPhase(r.data.status === 'pending_approval' ? 'confirm' : 'gone')
      })
      .catch(exc => {
        setError(exc instanceof ApiError ? exc.message : 'Failed to load action')
        setPhase('failed')
      })
  }, [actionId])

  const approve = async () => {
    setPhase('executing')
    try {
      const resp = await api.post<{ data: PayPalAction }>(
        `/paypal/actions/${actionId}/complete`)
      setAction(resp.data)
      setPhase('done')
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Execution failed')
      setPhase('failed')
    }
  }

  const reject = async () => {
    try {
      await api.post(`/paypal/actions/${actionId}/reject`)
    } catch { /* audit already shows the attempt */ }
    setPhase('gone')
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-6 py-12">
      <div className="w-full max-w-[460px]">
        <Brand />

        {phase === 'loading' && <Loading text="Preparing approval…" />}

        {phase === 'confirm' && action && (
          <div className="panel px-6 py-6">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-spark">
              Step 1 of 2 · Approval required
            </p>
            <h1 className="mt-2 font-display text-xl font-bold text-fog-bright">
              {cap(action.action_type)} “{action.subscription_name}”
            </h1>
            <p className="mt-2 text-[13px] leading-relaxed text-fog">
              The AI proposed this action{action.reason ? ` — ${action.reason}` : ''}.
              Nothing has happened yet. Approving will execute it and write an
              audit record.
            </p>

            <dl className="mt-5 flex flex-col gap-2.5 border-t border-hairline pt-4 text-[13px]">
              {action.amount !== null && (
                <Detail label="Amount" value={money(action.amount, action.currency === 'USD' ? '$' : '')} />
              )}
              {action.estimated_monthly_savings !== null && (
                <Detail label="Estimated savings"
                        value={`${money(action.estimated_monthly_savings)}/mo`}
                        tone="text-spark" />
              )}
              <Detail label="PayPal subscription"
                      value={action.paypal_subscription_id ?? '—'} mono />
              <Detail label="Execution mode" value={action.paypal_mode} mono />
            </dl>

            {error && <p className="mt-4 text-xs text-coral">{error}</p>}

            <div className="mt-6 flex gap-3">
              <button onClick={approve} className="btn flex-1 bg-[#FFC439]
                                                   text-[#0B1A33] hover:bg-[#FFD46B]">
                <Zap className="h-4 w-4" fill="currentColor" strokeWidth={1} />
                Approve & execute
              </button>
              <button onClick={reject} className="btn-ghost">Reject</button>
            </div>

            <p className="mt-4 flex items-start gap-2 text-[11px] leading-relaxed text-fog-dim">
              <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              Human-in-the-loop: the AI can only propose. Execution requires
              this click and is recorded in the audit trail.
            </p>
          </div>
        )}

        {phase === 'executing' && <Loading text="Executing through PayPal…" />}

        {phase === 'done' && action && <DoneCard action={action} />}

        {phase === 'gone' && (
          <Notice
            icon={<XCircle className="h-5 w-5 text-fog" />}
            title="Action no longer pending"
            body="This proposal was already executed or rejected. Check the Action Log for its record."
          />
        )}

        {phase === 'failed' && (
          <Notice
            icon={<XCircle className="h-5 w-5 text-coral" />}
            title="Something went wrong"
            body={error ?? 'Unknown error.'}
            back
          />
        )}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */

export function DoneCard({ action }: { action: PayPalAction }) {
  const counted = useCountUp(action.estimated_monthly_savings ?? 0)

  return (
    <div className="panel spark-pulse px-6 py-6">
      <div className="flex items-center gap-2.5">
        <CheckCircle2 className="h-5 w-5 text-mint" />
        <h1 className="font-display text-xl font-bold text-fog-bright">
          Done — via PayPal
        </h1>
      </div>

      <p className="mt-2 text-[13px] leading-relaxed text-fog">
        {cap(action.action_type)} of “{action.subscription_name}” completed
        {action.paypal_mode === 'sandbox' ? ' against the PayPal sandbox'
                                          : ' in simulation mode'}.
      </p>

      {action.estimated_monthly_savings !== null && (
        <div className="mt-5 rounded-xl border border-spark/25 bg-spark-dim/40
                        px-4 py-4 text-center">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-fog">
            Estimated savings
          </p>
          <p className="tnum mt-1 text-3xl font-bold text-spark">
            {money(counted)}/mo
          </p>
          <p className="tnum mt-1 text-xs text-fog">
            ≈ {money((action.estimated_monthly_savings ?? 0) * 12)}/year
          </p>
        </div>
      )}

      <dl className="mt-5 flex flex-col gap-2.5 border-t border-hairline pt-4 text-[13px]">
        <Detail label="Executed at" value={dateTime(action.executed_at)} mono />
        {action.paypal_subscription_id && (
          <Detail label="PayPal subscription" value={action.paypal_subscription_id} mono />
        )}
        {action.paypal_order_id && (
          <Detail label="PayPal order" value={action.paypal_order_id} mono />
        )}
        {action.paypal_capture_id && (
          <Detail label="Capture id" value={action.paypal_capture_id} mono />
        )}
      </dl>

      <div className="mt-6 flex gap-3">
        <Link to="/dashboard" className="btn-primary flex-1">
          <ArrowLeft className="h-4 w-4" /> Back to dashboard
        </Link>
        <Link to="/actions" className="btn-ghost">Action Log</Link>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */

function Brand() {
  return (
    <div className="mb-6 flex flex-col items-center text-center">
      <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-bolt shadow-panel">
        <Zap className="h-5 w-5 text-white" fill="currentColor" strokeWidth={1} />
      </span>
      <p className="font-display text-lg font-bold tracking-tight text-fog-bright">
        Spark2Pay
      </p>
    </div>
  )
}

function Loading({ text }: { text: string }) {
  return (
    <div className="panel flex items-center justify-center gap-3 px-6 py-12 text-fog">
      <Loader2 className="h-5 w-5 spinner" />
      <span className="text-sm">{text}</span>
    </div>
  )
}

export function Notice({ icon, title, body, back }: {
  icon?: React.ReactNode; title: string; body: string; back?: boolean
}) {
  return (
    <div className="panel px-6 py-6 text-center">
      {icon && (
        <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center">
          {icon}
        </div>
      )}
      <h1 className="font-display text-lg font-bold text-fog-bright">{title}</h1>
      <p className="mt-2 text-[13px] leading-relaxed text-fog">{body}</p>
      {back && (
        <Link to="/dashboard" className="btn-ghost mt-5">
          <ArrowLeft className="h-4 w-4" /> Back to dashboard
        </Link>
      )}
    </div>
  )
}

function Detail({ label, value, tone, mono }: {
  label: string; value: string; tone?: string; mono?: boolean
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-fog">{label}</dt>
      <dd className={`${mono ? 'tnum' : ''} text-right text-fog-bright ${tone ?? ''}`}>
        {value}
      </dd>
    </div>
  )
}

function cap(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}
