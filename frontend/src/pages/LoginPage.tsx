import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Zap, Loader2, ArrowRight } from 'lucide-react'
import { api, setToken, ApiError } from '../lib/api'

export default function LoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const resp = await api.post<{ token: string }>('/auth/login', {
        username, password
      })
      setToken(resp.token)
      navigate('/dashboard')
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Login failed')
      setBusy(false)
    }
  }

  const useDemo = () => {
    setUsername('demo')
    setPassword('Spark2Pay2026')
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-[400px]">
        {/* Brand */}
        <div className="mb-8 flex flex-col items-center text-center">
          <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-bolt shadow-panel">
            <Zap className="h-6 w-6 text-white" fill="currentColor" strokeWidth={1} />
          </span>
          <h1 className="font-display text-3xl font-bold tracking-tight text-fog-bright">
            Spark2Pay
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-fog">
            The agentic subscription manager.<br />
            AI finds the waste. <span className="text-spark">PayPal executes the savings.</span>
          </p>
        </div>

        <form onSubmit={submit} className="panel px-6 py-6">
          <div className="mb-4">
            <label className="label" htmlFor="username">Username</label>
            <input id="username" className="input" value={username}
                   onChange={e => setUsername(e.target.value)}
                   placeholder="demo" autoComplete="username" required />
          </div>
          <div className="mb-5">
            <label className="label" htmlFor="password">Password</label>
            <input id="password" className="input" type="password" value={password}
                   onChange={e => setPassword(e.target.value)}
                   placeholder="••••••••" autoComplete="current-password" required />
          </div>

          {error && (
            <p className="mb-4 rounded-lg border border-coral/30 bg-coral-dim px-3 py-2
                          text-xs leading-relaxed text-coral">
              {error}
            </p>
          )}

          <button type="submit" disabled={busy} className="btn-primary w-full">
            {busy ? <Loader2 className="h-4 w-4 spinner" /> : null}
            {busy ? 'Signing in…' : 'Sign in'}
            {!busy && <ArrowRight className="h-4 w-4" />}
          </button>

          <button type="button" onClick={useDemo}
                  className="mt-3 w-full text-center text-xs text-fog-dim
                             transition-colors hover:text-bolt-soft">
            Use the demo account (demo / Spark2Pay2026)
          </button>
        </form>
      </div>
    </div>
  )
}
