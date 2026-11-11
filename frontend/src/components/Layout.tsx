import { NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Repeat, ScrollText, Settings, Zap, LogOut } from 'lucide-react'
import { clearToken } from '../lib/api'

const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/subscriptions', label: 'Subscriptions', icon: Repeat },
  { to: '/actions', label: 'Action Log', icon: ScrollText },
  { to: '/settings', label: 'Settings', icon: Settings }
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()

  const logout = () => {
    clearToken()
    navigate('/login')
  }

  return (
    <div className="flex min-h-screen">
      {/* Sidebar - one nav, equal edges */}
      <aside className="fixed inset-y-0 left-0 flex w-60 flex-col border-r border-hairline bg-ink-950/60 px-4 py-6">
        <div className="flex items-center gap-2.5 px-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-bolt shadow-panel">
            <Zap className="h-4.5 w-4.5 text-white" fill="currentColor" strokeWidth={1} />
          </span>
          <div>
            <p className="font-display text-[17px] font-bold leading-none tracking-tight text-fog-bright">
              Spark2Pay
            </p>
            <p className="mt-1 text-[10px] font-medium uppercase tracking-[0.14em] text-fog-dim">
              Agentic Subscriptions
            </p>
          </div>
        </div>

        <nav className="mt-8 flex flex-1 flex-col gap-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-bolt-dim/40 text-fog-bright'
                    : 'text-fog hover:bg-ink-800 hover:text-fog-bright'
                }`
              }
            >
              <Icon className="h-4 w-4" strokeWidth={1.8} />
              {label}
            </NavLink>
          ))}
        </nav>

        <button onClick={logout}
                className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-fog transition-colors hover:bg-ink-800 hover:text-coral">
          <LogOut className="h-4 w-4" strokeWidth={1.8} />
          Sign out
        </button>
      </aside>

      {/* Content - consistent horizontal rhythm everywhere */}
      <main className="ml-60 flex-1">
        <div className="mx-auto w-full max-w-[1080px] px-8 py-8">
          {children}
        </div>
      </main>
    </div>
  )
}
