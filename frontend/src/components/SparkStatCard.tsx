import { useEffect, useRef, useState } from 'react'

/** Count-up animation - the "dealt moment" when savings land. */
export function useCountUp(target: number, duration = 900): number {
  const [value, setValue] = useState(0)
  const raf = useRef<number>(0)

  useEffect(() => {
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      setValue(target * eased)
      if (t < 1) raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf.current)
  }, [target, duration])

  return value
}

interface StatProps {
  label: string
  value: string
  sub?: string
  tone?: 'default' | 'spark' | 'mint' | 'coral'
  icon?: React.ReactNode
  pulse?: boolean
}

export default function SparkStatCard({ label, value, sub, tone = 'default',
                                        icon, pulse }: StatProps) {
  const toneClass = {
    default: 'text-fog-bright',
    spark: 'text-spark',
    mint: 'text-mint',
    coral: 'text-coral'
  }[tone]

  return (
    <div className={`panel panel-hover px-5 py-4 ${pulse ? 'spark-pulse' : ''}`}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-fog-dim">
          {label}
        </p>
        {icon && <span className="text-fog-dim">{icon}</span>}
      </div>
      <p className={`tnum mt-2 text-[26px] font-semibold leading-none ${toneClass}`}>
        {value}
      </p>
      {sub && <p className="mt-2 text-xs text-fog">{sub}</p>}
    </div>
  )
}
