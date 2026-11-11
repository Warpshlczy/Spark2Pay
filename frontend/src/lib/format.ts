/* Formatting helpers - every number renders in JetBrains Mono via .tnum */

export function money(amount: number | null | undefined, symbol = '$',
                      digits = 2): string {
  if (amount === null || amount === undefined) return '—'
  return `${symbol}${amount.toFixed(digits)}`
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric',
                                         year: 'numeric' })
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

export function daysUntil(iso: string | null | undefined): number | null {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return Math.ceil((d.getTime() - Date.now()) / 86400000)
}

export function cycleName(cycle: number, frequency: number): string {
  const names: Record<number, string> = { 1: 'Daily', 2: 'Weekly',
                                          3: 'Monthly', 4: 'Yearly' }
  if (frequency === 1) return names[cycle] ?? 'Unknown'
  const unit = { 1: 'days', 2: 'weeks', 3: 'months', 4: 'years' }[cycle]
  return `Every ${frequency} ${unit}`
}

/** Monthly-equivalent cost, mirroring the backend BillingCycleCalculator. */
export function monthlyCost(price: number, cycle: number,
                            frequency: number): number {
  if (cycle === 1) return (price / frequency) * 30.44
  if (cycle === 2) return (price / frequency) * 4.33
  if (cycle === 3) return price / frequency
  if (cycle === 4) return price / (frequency * 12)
  return price
}
