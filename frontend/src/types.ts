/* Shared API types for Spark2Pay */

export interface Currency {
  id: number
  name: string
  code: string
  symbol: string
  rate: number
}

export interface Category {
  id: number
  name: string
  order: number
}

export interface Subscription {
  id: number
  name: string
  price: number
  currency: Currency | null
  cycle: number // 1=days, 2=weeks, 3=months, 4=years
  frequency: number
  next_payment: string | null
  auto_renew: boolean
  logo: string | null
  url: string | null
  notes: string | null
  category: Category | null
  payment_method: { id: number; name: string } | null
  inactive: boolean
  cancellation_date: string | null
  paypal_subscription_id: string | null
  created_at: string
  updated_at: string
}

export interface UsageInfo {
  subscription_id: number
  last_used_at: string | null
  usage_count_30d: number
}

export interface Advice {
  subscription_id: number
  title: string
  recommended_action: 'cancel' | 'optimize' | 'suspend' | 'activate'
  rationale: string
  estimated_monthly_savings: number
  confidence: number
  action_available: boolean
  subscription?: {
    id: number
    name: string
    price: number
    currency: string
    currency_symbol: string
    category: string | null
    next_payment: string | null
    paypal_managed: boolean
  }
}

export interface AdviceResponse {
  engine: 'openai' | 'heuristic'
  note: string | null
  summary: string | null
  paypal_mode: 'sandbox' | 'simulation'
  advice: Advice[]
}

export type ActionType = 'cancel' | 'suspend' | 'activate' | 'pay'

export interface PayPalAction {
  id: number
  user_id: number
  subscription_id: number | null
  subscription_name: string | null
  action_type: ActionType
  status:
    | 'pending_approval'
    | 'executing'
    | 'completed'
    | 'failed'
    | 'rejected'
  reason: string | null
  amount: number | null
  currency: string | null
  estimated_monthly_savings: number | null
  paypal_order_id: string | null
  paypal_capture_id: string | null
  paypal_subscription_id: string | null
  paypal_mode: string
  payload: Record<string, unknown>
  error: string | null
  created_at: string | null
  executed_at: string | null
}

export interface BeginActionResponse {
  action_id: number
  status: string
  action_type: ActionType
  approve_link: string
  estimated_monthly_savings: number | null
  mode: string
}

export interface AIStatus {
  ai: {
    configured_provider: string
    effective_provider: string
    model: string
    openai: boolean
    gemini: boolean
    ollama_host: string
  }
  paypal: {
    mode: 'sandbox' | 'simulation'
    sandbox_configured: boolean
  }
}

export interface SettingsStatus {
  ai: {
    configured_provider: string
    effective_provider: string
    model: string
    openai_key: string | null
  }
  execution: {
    mode: 'sandbox' | 'simulation'
    client_id: string | null
    client_secret: string | null
    webhook_id: string | null
  }
  editable_keys: string[]
}

export interface User {
  id: number
  username: string
  email: string
  firstname: string | null
  budget: number | null
}
