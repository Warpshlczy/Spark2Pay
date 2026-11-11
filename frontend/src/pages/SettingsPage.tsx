import { useEffect, useState } from 'react'
import { Zap, Bot, ShieldCheck, Loader2, CheckCircle2, XCircle } from 'lucide-react'
import { api } from '../lib/api'
import type { AIStatus } from '../types'

export default function SettingsPage() {
  const [status, setStatus] = useState<AIStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<{ data: AIStatus }>('/ai/status')
      .then(r => setStatus(r.data))
      .catch(exc => setError(exc instanceof Error ? exc.message : 'Load failed'))
  }, [])

  if (!status && !error) {
    return (
      <div className="flex h-[60vh] items-center justify-center gap-3 text-fog">
        <Loader2 className="h-5 w-5 spinner" />
        <span className="text-sm">Loading configuration…</span>
      </div>
    )
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="font-display text-[26px] font-bold tracking-tight text-fog-bright">
          Settings
        </h1>
        <p className="mt-1 text-sm text-fog">
          Live configuration of the AI engine and the PayPal execution layer
        </p>
      </header>

      {error && (
        <p className="panel mb-6 border-coral/30 px-4 py-3 text-xs text-coral">{error}</p>
      )}

      {status && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* PayPal execution layer */}
          <section className="panel px-5 py-5">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg
                               bg-[#FFC439]/15">
                <Zap className="h-4 w-4 text-[#FFC439]" fill="currentColor" strokeWidth={1} />
              </span>
              <h2 className="text-sm font-semibold text-fog-bright">
                PayPal execution layer
              </h2>
            </div>

            <dl className="mt-4 flex flex-col gap-3 text-[13px]">
              <Row label="Mode">
                <span className={`tnum rounded border px-2 py-0.5 text-[11px] font-semibold
                                  ${status.paypal.mode === 'sandbox'
                                    ? 'border-bolt/30 bg-bolt-dim/40 text-bolt-soft'
                                    : 'border-hairline bg-ink-800 text-fog'}`}>
                  {status.paypal.mode}
                </span>
              </Row>
              <Row label="Sandbox credentials">
                <Check status={status.paypal.sandbox_configured} />
              </Row>
              <Row label="Orders v2 (pay)">
                <span className="text-fog">ready</span>
              </Row>
              <Row label="Subscriptions v1 (cancel / suspend / activate)">
                <span className="text-fog">ready</span>
              </Row>
            </dl>

            {status.paypal.mode === 'simulation' && (
              <p className="mt-4 rounded-lg border border-hairline bg-ink-800 px-3.5 py-3
                            text-xs leading-relaxed text-fog">
                Simulation mode executes every action against a deterministic
                local simulator - the full audit loop runs without PayPal
                credentials. Add <code className="tnum text-spark">PAYPAL_MODE=sandbox</code>{' '}
                plus your sandbox client keys in <code className="tnum text-spark">.env</code>{' '}
                to hit the real PayPal sandbox.
              </p>
            )}
          </section>

          {/* AI engine */}
          <section className="panel px-5 py-5">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg
                               bg-bolt-dim/50">
                <Bot className="h-4 w-4 text-bolt-soft" />
              </span>
              <h2 className="text-sm font-semibold text-fog-bright">AI savings engine</h2>
            </div>

            <dl className="mt-4 flex flex-col gap-3 text-[13px]">
              <Row label="Configured provider">
                <span className="tnum text-fog-bright">
                  {status.ai.configured_provider}
                </span>
              </Row>
              <Row label="Effective engine">
                <span className="tnum font-semibold text-bolt-soft">
                  {status.ai.effective_provider}
                </span>
              </Row>
              <Row label="Model">
                <span className="tnum text-fog">{status.ai.model}</span>
              </Row>
              <Row label="OpenAI key">
                <Check status={status.ai.openai} />
              </Row>
              <Row label="Gemini key">
                <Check status={status.ai.gemini} />
              </Row>
              <Row label="Fallback">
                <span className="text-fog">deterministic rules engine (always on)</span>
              </Row>
            </dl>
          </section>

          {/* Safety */}
          <section className="panel px-5 py-5 lg:col-span-2">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg
                               bg-mint-dim">
                <ShieldCheck className="h-4 w-4 text-mint" />
              </span>
              <h2 className="text-sm font-semibold text-fog-bright">
                Human-in-the-loop guarantee
              </h2>
            </div>
            <p className="mt-3 max-w-[720px] text-[13px] leading-relaxed text-fog">
              The AI can only <em>propose</em> PayPal actions. Every proposal
              becomes a button, every button requires your explicit approval,
              and every execution is written to an immutable audit trail in the
              Action Log. No money moves and no subscription changes without a
              human click.
            </p>
          </section>
        </div>
      )}
    </div>
  )
}

function Row({ label, children }: { label: string;
                                    children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-fog">{label}</dt>
      <dd className="text-right">{children}</dd>
    </div>
  )
}

function Check({ status }: { status: boolean }) {
  return status
    ? <span className="inline-flex items-center gap-1 text-xs font-medium text-mint">
        <CheckCircle2 className="h-3.5 w-3.5" /> configured
      </span>
    : <span className="inline-flex items-center gap-1 text-xs font-medium text-fog-dim">
        <XCircle className="h-3.5 w-3.5" /> not set
      </span>
}
