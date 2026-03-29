const API_BASE = import.meta.env.VITE_API_BASE_URL?.trim() || ''

type ApiErrorPayload = {
  error?: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
}

export class ApiError extends Error {
  status: number
  code: string
  details?: Record<string, unknown>

  constructor(status: number, code: string, message: string, details?: Record<string, unknown>) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })

  if (response.status === 204) {
    return undefined as T
  }

  const data = (await response.json()) as T | ApiErrorPayload

  if (!response.ok) {
    const payload = data as ApiErrorPayload
    const error = payload.error
    throw new ApiError(
      response.status,
      error?.code ?? 'bad_request',
      error?.message ?? 'Unexpected API error.',
      error?.details,
    )
  }

  return data as T
}
