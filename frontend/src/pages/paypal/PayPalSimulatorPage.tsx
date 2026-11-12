/**
 * PayPal-styled approval simulator (simulation mode only).
 *
 * Mimics the shape of the real PayPal checkout approval - light theme,
 * PayPal wordmark, sandbox buyer account, Agree & Pay / Cancel buttons -
 * so the demo shows the true flow shape: approve on PayPal, return to the
 * merchant, capture/cancel. With real sandbox credentials the pay flow
 * opens PayPal's hosted approval page instead; this simulator exists so
 * the full loop is demonstrable without credentials.
 *
 * The banner says exactly what this is: a sandbox simulation, no real money.
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Loader2, ShieldCheck, Lock } from 'lucide-react'
import { api, ApiError } from '../../lib/api'
import type { PayPalAction } from '../../types'

type Phase = 'loading' | 'ready' | 'executing' | 'error'

export default function PayPalSimulatorPage() {
  const { actionId } = useParams()
  const navigate = useNavigate()
  const [phase, setPhase] = useState<Phase>('loading')
  const [action, setAction] = useState<PayPalAction | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<{ data: PayPalAction }>(`/paypal/actions/${actionId}`)
      .then(r => {
        setAction(r.data)
        setPhase(r.data.status === 'pending_approval' ? 'ready' : 'error')
        if (r.data.status !== 'pending_approval') {
          setError('This approval is no longer pending. It may have already been processed.')
        }
      })
      .catch(exc => {
        setError(exc instanceof ApiError ? exc.message : 'Failed to load the order')
        setPhase('error')
      })
  }, [actionId])

  const approve = async () => {
    setPhase('executing')
    try {
      await api.post(`/paypal/actions/${actionId}/complete`)
      // Return to the merchant (Spark2Pay) - the done page picks up there
      navigate(`/paypal/approve/${actionId}`)
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Execution failed')
      setPhase('error')
    }
  }

  const cancelAndReturn = async () => {
    try {
      await api.post(`/paypal/actions/${actionId}/reject`)
    } catch { /* audit already shows the attempt */ }
    navigate('/dashboard')
  }

  /* ---------------- chrome ---------------- */

  if (phase === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f5f7fa]">
        <Loader2 className="h-6 w-6 spinner text-[#0070BA]" />
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f5f7fa] px-6">
        <div className="w-full max-w-[440px] rounded-xl bg-white p-8 text-center shadow-sm">
          <Wordmark />
          <p className="mt-6 text-[15px] text-[#2c2e2f]">{error}</p>
          <button onClick={() => navigate('/dashboard')}
                  className="mt-6 h-11 w-full rounded-full bg-[#0070BA] text-sm
                             font-semibold text-white hover:bg-[#005ea6]">
            Return to Spark2Pay
          </button>
        </div>
      </div>
    )
  }

  const amountLine = action?.action_type === 'pay' && action.amount !== null
    ? `${action.currency === 'USD' ? '$' : ''}${action.amount.toFixed(2)} ${action.currency ?? ''}`
    : null
  const approveLabel = {
    pay: `Agree & Pay Now${amountLine ? ` ${amountLine.split(' ')[0]}` : ''}`,
    cancel: 'Agree & Cancel Subscription',
    suspend: 'Agree & Suspend',
    activate: 'Agree & Reactivate'
  }[action?.action_type ?? 'pay']

  return (
    <div className="min-h-screen bg-[#f5f7fa] font-sans text-[#2c2e2f]">
      {/* Sandbox notice */}
      <div className="bg-[#2c2e2f] px-4 py-1.5 text-center text-[11px] font-medium
                      text-white/90">
        SANDBOX ENVIRONMENT — simulated approval, no real money moves
      </div>

      {/* PayPal header */}
      <header className="border-b border-[#e5e5e5] bg-white">
        <div className="mx-auto flex max-w-[960px] items-center justify-between px-6 py-4">
          <Wordmark />
          <span className="flex items-center gap-1.5 text-xs text-[#545454]">
            <Lock className="h-3.5 w-3.5" /> Secure checkout
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-[960px] px-6 py-8">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-[1fr_320px]">
          {/* Left: account + action */}
          <div>
            <h1 className="text-[22px] font-semibold">
              {action?.action_type === 'pay'
                ? 'Choose how to pay'
                : 'Manage your billing agreement'}
            </h1>
            <p className="mt-1 text-sm text-[#545454]">
              Spark2Pay requests this change through PayPal Subscriptions.
            </p>

            {/* Simulated account */}
            <div className="mt-5 rounded-lg border border-[#d8d8d8] bg-white p-4">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-full
                                 bg-[#0070BA] text-sm font-bold text-white">B</span>
                <div className="flex-1">
                  <p className="text-sm font-semibold">buyer@personal.example.com</p>
                  <p className="text-xs text-[#545454]">Sandbox personal account</p>
                </div>
                <span className="rounded bg-[#f0f6fb] px-2 py-1 text-[10px] font-bold
                                 uppercase tracking-wide text-[#0070BA]">
                  PayPal balance
                </span>
              </div>
              <div className="mt-3 border-t border-[#ebebeb] pt-3 text-sm
                              flex items-center justify-between">
                <span className="text-[#545454]">Available</span>
                <span className="tnum font-semibold">$3,500.00 USD</span>
              </div>
            </div>

            {/* Action detail */}
            {action && (
              <div className="mt-4 rounded-lg border border-[#d8d8d8] bg-white p-4 text-sm">
                <p className="font-semibold">
                  {cap(action.action_type)} “{action.subscription_name}”
                </p>
                <p className="mt-1 text-[13px] leading-relaxed text-[#545454]">
                  {action.reason || 'Requested via Spark2Pay'} · Billing
                  agreement {action.paypal_subscription_id}
                </p>
                {action.estimated_monthly_savings !== null && (
                  <p className="mt-2 text-[13px]">
                    Monthly charge after this change:{' '}
                    <span className="tnum font-semibold text-[#00804a]">
                      −${action.estimated_monthly_savings.toFixed(2)}
                    </span>
                  </p>
                )}
              </div>
            )}

            {error && (
              <p className="mt-4 rounded-lg bg-[#fdf0f0] px-4 py-3 text-xs
                            text-[#b42318]">{error}</p>
            )}

            {/* Buttons */}
            <div className="mt-6 flex flex-col gap-3">
              <button onClick={approve} disabled={phase === 'executing'}
                      className="h-12 rounded-full bg-[#FFC439] text-[15px]
                                 font-bold text-[#2c2e2f] transition-colors
                                 hover:bg-[#f2ba36] disabled:opacity-50">
                {phase === 'executing'
                  ? <Loader2 className="mr-2 inline h-4 w-4 spinner" />
                  : null}
                {approveLabel}
              </button>
              <button onClick={cancelAndReturn}
                      className="text-sm font-medium text-[#0070BA]
                                 hover:underline">
                Cancel and return to Spark2Pay
              </button>
            </div>

            <p className="mt-6 flex items-start gap-2 text-[11px] leading-relaxed
                          text-[#8c8c8c]">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
              Simulated sandbox approval for the Spark2Pay demo. With real
              sandbox credentials configured, pay orders open PayPal's hosted
              approval page instead.
            </p>
          </div>

          {/* Right: order summary */}
          <aside>
            <div className="rounded-xl border border-[#d8d8d8] bg-white p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-[#545454]">
                Order summary
              </p>
              <div className="mt-3 flex items-baseline justify-between">
                <span className="text-sm text-[#545454]">Merchant</span>
                <span className="text-sm font-semibold">Spark2Pay</span>
              </div>
              {amountLine && (
                <div className="mt-2 flex items-baseline justify-between">
                  <span className="text-sm text-[#545454]">Total</span>
                  <span className="tnum text-xl font-bold">{amountLine}</span>
                </div>
              )}
              {action?.estimated_monthly_savings !== null &&
               action?.action_type !== 'pay' && (
                <div className="mt-2 flex items-baseline justify-between">
                  <span className="text-sm text-[#545454]">Recurring charge</span>
                  <span className="tnum text-sm font-semibold line-through
                                   text-[#8c8c8c]">
                    ${action?.estimated_monthly_savings?.toFixed(2)}/mo
                  </span>
                </div>
              )}
              <div className="mt-4 border-t border-[#ebebeb] pt-3 text-[11px]
                              leading-relaxed text-[#8c8c8c]">
                Execution mode: <span className="tnum">{action?.paypal_mode}</span> ·
                Agreement <span className="tnum">{action?.paypal_subscription_id}</span>
              </div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  )
}

/* ------------------------------------------------------------------ */

function Wordmark() {
  return (
    <span className="select-none text-2xl font-extrabold italic tracking-tight">
      <span className="text-[#003087]">Pay</span><span className="text-[#0070BA]">Pal</span>
      <span className="ml-2 align-middle rounded bg-[#f0f6fb] px-1.5 py-0.5
                       text-[9px] font-bold not-italic uppercase tracking-widest
                       text-[#0070BA]">Sandbox</span>
    </span>
  )
}

function cap(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}
