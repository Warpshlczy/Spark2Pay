/**
 * Return landing after a PayPal-hosted approval (pay orders in sandbox mode).
 * PayPal redirects here with ?token=<order token>&action_id=<our audit id>;
 * we complete the capture and show the result.
 */
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { api, ApiError } from '../../lib/api'
import type { PayPalAction } from '../../types'
import { DoneCard, Notice } from './PayPalApprovePage'

export default function PayPalReturnPage() {
  const [params] = useSearchParams()
  const actionId = params.get('action_id')
  const [phase, setPhase] = useState<'loading' | 'done' | 'failed'>('loading')
  const [action, setAction] = useState<PayPalAction | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!actionId) {
      setError('Missing action_id in the return URL.')
      setPhase('failed')
      return
    }
    api.post<{ data: PayPalAction }>(`/paypal/actions/${actionId}/complete`)
      .then(r => {
        setAction(r.data)
        setPhase('done')
      })
      .catch(exc => {
        // Idempotency: the capture may already have completed via webhook
        if (exc instanceof ApiError && exc.status === 409) {
          return api.get<{ data: PayPalAction }>(`/paypal/actions/${actionId}`)
            .then(r => { setAction(r.data); setPhase('done') })
        }
        setError(exc instanceof ApiError ? exc.message : 'Capture failed')
        setPhase('failed')
      })
  }, [actionId])

  if (phase === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center gap-3 text-fog">
        <Loader2 className="h-5 w-5 spinner" />
        <span className="text-sm">Capturing your approved payment…</span>
      </div>
    )
  }

  if (phase === 'failed') {
    return (
      <div className="flex min-h-screen items-center justify-center px-6">
        <div className="w-full max-w-[460px]">
          <Notice title="Could not complete the payment"
                  body={error ?? 'Unknown error.'} back />
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-6 py-12">
      <div className="w-full max-w-[460px]">
        {action && <DoneCard action={action} />}
      </div>
    </div>
  )
}
