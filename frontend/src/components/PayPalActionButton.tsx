import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Zap, Loader2 } from 'lucide-react'
import { api, ApiError } from '../lib/api'
import type { ActionType, BeginActionResponse } from '../types'

interface Props {
  subscriptionId: number
  actionType: ActionType
  reason: string
  label?: string
  onDone?: () => void
  className?: string
}

/**
 * The "last mile" button: begins a PayPal-backed action, sends the user
 * through the approval step (PayPal-hosted for pay orders in sandbox mode,
 * Spark2Pay's own confirm page for manage-subscription actions), and calls
 * back when the loop finishes.
 */
export default function PayPalActionButton({
  subscriptionId, actionType, reason, label, onDone, className
}: Props) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const click = async () => {
    setBusy(true)
    setError(null)
    try {
      const resp = await api.post<{ data: BeginActionResponse }>(
        '/paypal/actions',
        {
          subscription_id: subscriptionId,
          action_type: actionType,
          reason,
          origin: 'ai_recommendation'
        }
      )
      const { approve_link: link, mode } = resp.data

      if (link.startsWith('/')) {
        // Local confirmation step (cancel/suspend/activate)
        navigate(link)
      } else if (mode === 'simulation') {
        // Simulated hosted approval lands on our return page
        window.location.href = link
      } else {
        // Real PayPal-hosted approval (sandbox/live pay orders)
        window.location.href = link
      }
    } catch (exc) {
      if (exc instanceof ApiError) {
        setError(
          exc.code === 'not_paypal_managed'
            ? 'This subscription is billed by card — cancel it on the merchant site.'
            : exc.message
        )
      } else {
        setError('Something went wrong starting this action.')
      }
      setBusy(false)
      onDone?.()
    }
  }

  return (
    <div className={className}>
      <button onClick={click} disabled={busy}
              className="btn bg-[#FFC439] text-[#0B1A33] hover:bg-[#FFD46B]
                         font-semibold shadow-panel">
        {busy
          ? <Loader2 className="h-4 w-4 spinner" />
          : <Zap className="h-4 w-4" fill="currentColor" strokeWidth={1} />}
        {busy ? 'Opening approval…' : label ?? 'Manage with PayPal'}
      </button>
      {error && <p className="mt-2 text-xs leading-relaxed text-coral">{error}</p>}
    </div>
  )
}
