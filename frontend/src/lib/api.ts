/* Tiny JWT-carrying API client for the Spark2Pay backend */

export class ApiError extends Error {
  status: number
  code?: string

  constructor(status: number, message: string, code?: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

const TOKEN_KEY = 's2p_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string>)
  }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let resp: Response
  try {
    resp = await fetch(`/api/v1${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, 'Cannot reach the Spark2Pay backend. Is it running on port 3038?')
  }

  let body: Record<string, unknown> = {}
  try {
    body = await resp.json()
  } catch {
    /* non-JSON response (e.g. 204) */
  }

  if (!resp.ok) {
    if (resp.status === 401) clearToken()
    throw new ApiError(
      resp.status,
      (body.message as string) || `Request failed (${resp.status})`,
      body.code as string | undefined
    )
  }
  return body as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'POST', body: data ? JSON.stringify(data) : undefined })
}
