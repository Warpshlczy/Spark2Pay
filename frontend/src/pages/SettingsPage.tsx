import { useCallback, useEffect, useState } from 'react'
import { Zap, Bot, ShieldCheck, Loader2, Cog, Check } from 'lucide-react'
import { api } from '../lib/api'
import type { SettingsStatus } from '../types'

export default function SettingsPage() {
  const [status, setStatus] = useState<SettingsStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api.get<{ data: SettingsStatus }>('/settings')
      .then(r => setStatus(r.data))
      .catch(exc => setError(exc instanceof Error ? exc.message : 'Load failed'))
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div>
      <header className="mb-6">
        <h1 className="font-display text-[26px] font-bold tracking-tight text-fog-bright">
          Settings
        </h1>
        <p className="mt-1 text-sm text-fog">
          Live configuration — click any card to configure it. Values are
          stored locally in this instance.
        </p>
      </header>

      {error && (
        <p className="panel mb-6 border-coral/30 px-4 py-3 text-xs text-coral">{error}</p>
      )}

      {status && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <AICard status={status} onSaved={load} />
          <ExecutionCard status={status} onSaved={load} />

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
              The AI can only <em>propose</em> actions. Every proposal becomes a
              button, every button requires your explicit approval, and every
              execution is written to an immutable audit trail in the Action
              Log. No money moves and no subscription changes without a human
              click.
            </p>
          </section>
        </div>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* AI engine card                                                      */
/* ------------------------------------------------------------------ */

function AICard({ status, onSaved }: { status: SettingsStatus;
                                      onSaved: () => void }) {
  const [editing, setEditing] = useState(false)
  const [provider, setProvider] = useState(status.ai.configured_provider)
  const [model, setModel] = useState(status.ai.model || 'gpt-4o-mini')
  const [key, setKey] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const save = async () => {
    setBusy(true); setErr(null); setMsg(null)
    const body: Record<string, string> = {
      AI_PROVIDER: provider,
      AI_MODEL: model
    }
    if (key.trim()) body.OPENAI_API_KEY = key.trim()
    try {
      const resp = await api.post<{ message: string }>('/settings', body)
      setMsg(resp.message)
      setEditing(false)
      setKey('')
      onSaved()
    } catch (exc) {
      setErr(exc instanceof Error ? exc.message : 'Save failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel px-5 py-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg
                           bg-bolt-dim/50">
            <Bot className="h-4 w-4 text-bolt-soft" />
          </span>
          <h2 className="text-sm font-semibold text-fog-bright">AI savings engine</h2>
        </div>
        {!editing && (
          <button onClick={() => setEditing(true)} className="btn-ghost !h-8 !px-3 text-xs">
            <Cog className="h-3.5 w-3.5" /> Configure
          </button>
        )}
      </div>

      {editing ? (
        <div className="mt-4 flex flex-col gap-3">
          <div>
            <label className="label">Provider</label>
            <select value={provider} onChange={e => setProvider(e.target.value)}
                    className="input">
              <option value="auto">auto — LLM if a key exists, else rules engine</option>
              <option value="openai">openai</option>
              <option value="gemini">gemini</option>
              <option value="ollama">ollama (local)</option>
              <option value="heuristic">heuristic — built-in rules engine</option>
            </select>
          </div>
          <div>
            <label className="label">Model</label>
            <input className="input tnum" value={model}
                   onChange={e => setModel(e.target.value)} />
          </div>
          <div>
            <label className="label">OpenAI API key</label>
            <input className="input tnum" type="password" value={key}
                   onChange={e => setKey(e.target.value)}
                   placeholder={status.ai.openai_key ?? 'sk-… (leave blank to keep)'} />
          </div>
          {err && <p className="text-xs text-coral">{err}</p>}
          <div className="flex gap-2">
            <button onClick={save} disabled={busy} className="btn-primary !h-9 text-xs">
              {busy ? <Loader2 className="h-3.5 w-3.5 spinner" /> : <Check className="h-3.5 w-3.5" />}
              Save
            </button>
            <button onClick={() => setEditing(false)} className="btn-ghost !h-9 text-xs">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <dl className="mt-4 flex flex-col gap-3 text-[13px]">
          <Row label="Configured provider">
            <span className="tnum text-fog-bright">{status.ai.configured_provider}</span>
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
            {status.ai.openai_key
              ? <span className="tnum text-mint">{status.ai.openai_key}</span>
              : <span className="text-fog-dim">not set</span>}
          </Row>
          <Row label="Fallback">
            <span className="text-fog">rules engine (always on)</span>
          </Row>
          {msg && (
            <p className="flex items-center gap-1.5 text-xs text-mint">
              <Check className="h-3.5 w-3.5" /> {msg}
            </p>
          )}
        </dl>
      )}
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Execution layer card                                                */
/* ------------------------------------------------------------------ */

function ExecutionCard({ status, onSaved }: { status: SettingsStatus;
                                             onSaved: () => void }) {
  const [editing, setEditing] = useState(false)
  const [mode, setMode] = useState(status.execution.mode)
  const [clientId, setClientId] = useState(status.execution.client_id || '')
  const [secret, setSecret] = useState('')
  const [webhookId, setWebhookId] = useState(status.execution.webhook_id || '')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const save = async () => {
    setBusy(true); setErr(null); setMsg(null)
    const body: Record<string, string> = { PAYPAL_MODE: mode }
    if (clientId.trim()) body.PAYPAL_CLIENT_ID = clientId.trim()
    if (secret.trim()) body.PAYPAL_CLIENT_SECRET = secret.trim()
    if (webhookId.trim()) body.PAYPAL_WEBHOOK_ID = webhookId.trim()
    try {
      const resp = await api.post<{ message: string }>('/settings', body)
      setMsg(resp.message)
      setEditing(false)
      setSecret('')
      onSaved()
    } catch (exc) {
      setErr(exc instanceof Error ? exc.message : 'Save failed')
    } finally {
      setBusy(false)
    }
  }

  const connected = Boolean(status.execution.client_id &&
                            status.execution.client_secret)

  return (
    <section className="panel px-5 py-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg
                           bg-[#FFC439]/15">
            <Zap className="h-4 w-4 text-[#FFC439]" fill="currentColor" strokeWidth={1} />
          </span>
          <h2 className="text-sm font-semibold text-fog-bright">Execution layer</h2>
        </div>
        {!editing && (
          <button onClick={() => setEditing(true)} className="btn-ghost !h-8 !px-3 text-xs">
            <Cog className="h-3.5 w-3.5" /> Configure
          </button>
        )}
      </div>

      {editing ? (
        <div className="mt-4 flex flex-col gap-3">
          <div>
            <label className="label">Mode</label>
            <select value={mode} onChange={e => setMode(e.target.value as 'sandbox' | 'simulation')}
                    className="input">
              <option value="simulation">simulation — local demo, no credentials</option>
              <option value="sandbox">sandbox — real PayPal sandbox APIs</option>
            </select>
          </div>
          <div>
            <label className="label">Client ID</label>
            <input className="input tnum" value={clientId}
                   onChange={e => setClientId(e.target.value)} />
          </div>
          <div>
            <label className="label">Client secret</label>
            <input className="input tnum" type="password" value={secret}
                   onChange={e => setSecret(e.target.value)}
                   placeholder={status.execution.client_secret ?? 'leave blank to keep'} />
          </div>
          <div>
            <label className="label">Webhook ID (optional)</label>
            <input className="input tnum" value={webhookId}
                   onChange={e => setWebhookId(e.target.value)} />
          </div>
          {err && <p className="text-xs text-coral">{err}</p>}
          <div className="flex gap-2">
            <button onClick={save} disabled={busy} className="btn-primary !h-9 text-xs">
              {busy ? <Loader2 className="h-3.5 w-3.5 spinner" /> : <Check className="h-3.5 w-3.5" />}
              Save
            </button>
            <button onClick={() => setEditing(false)} className="btn-ghost !h-9 text-xs">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <dl className="mt-4 flex flex-col gap-3 text-[13px]">
          <Row label="Mode">
            <span className={`tnum rounded border px-2 py-0.5 text-[11px] font-semibold
                              ${status.execution.mode === 'sandbox'
                                ? 'border-bolt/30 bg-bolt-dim/40 text-bolt-soft'
                                : 'border-hairline bg-ink-800 text-fog'}`}>
              {status.execution.mode}
            </span>
          </Row>
          <Row label="Client ID">
            <span className="tnum text-fog-bright">
              {status.execution.client_id || 'not set'}
            </span>
          </Row>
          <Row label="Client secret">
            {status.execution.client_secret
              ? <span className="tnum text-mint">{status.execution.client_secret}</span>
              : <span className="text-fog-dim">not set</span>}
          </Row>
          <Row label="Webhook ID">
            <span className="tnum text-fog">
              {status.execution.webhook_id || 'not set'}
            </span>
          </Row>
          <Row label="Status">
            {connected && status.execution.mode === 'sandbox'
              ? <span className="text-mint">connected to sandbox</span>
              : <span className="text-fog">one-click execution ready</span>}
          </Row>
          {msg && (
            <p className="flex items-center gap-1.5 text-xs text-mint">
              <Check className="h-3.5 w-3.5" /> {msg}
            </p>
          )}
        </dl>
      )}

      {status.execution.mode === 'simulation' && !editing && (
        <p className="mt-4 rounded-lg border border-hairline bg-ink-800 px-3.5 py-3
                      text-xs leading-relaxed text-fog">
          Simulation mode executes every action against a deterministic local
          simulator — the full audit loop runs without credentials. Click
          <span className="text-spark"> Configure</span> and add sandbox keys to
          execute against the real PayPal sandbox.
        </p>
      )}
    </section>
  )
}

/* ------------------------------------------------------------------ */

function Row({ label, children }: { label: string;
                                    children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-fog">{label}</dt>
      <dd className="text-right">{children}</dd>
    </div>
  )
}
