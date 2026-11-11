/**
 * User hit "Cancel" on the PayPal approval screen (sandbox pay orders).
 * Record the rejection honestly in the audit trail.
 */
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../../lib/api'
import { Notice } from './PayPalApprovePage'

export default function PayPalCancelPage() {
  const [params] = useSearchParams()
  const actionId = params.get('action_id')
  const [recorded, setRecorded] = useState(false)

  useEffect(() => {
    if (actionId) {
      api.post(`/paypal/actions/${actionId}/reject`)
        .then(() => setRecorded(true))
        .catch(() => setRecorded(false))
    }
  }, [actionId])

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-[460px]">
        <Notice
          icon={<XCircleIcon />}
          title="Payment cancelled"
          body={recorded
            ? 'The approval was rejected and recorded in your Action Log. Nothing was charged.'
            : 'You returned without approving. Nothing was charged.'}
          back
        />
      </div>
    </div>
  )
}

function XCircleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5 text-fog" fill="none"
         stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M9 9l6 6M15 9l-6 6" />
    </svg>
  )
}
