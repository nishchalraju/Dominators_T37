import { ApiError, isAbort } from '@/utils/errors'

type QueryValue = string | number | boolean | null | undefined
export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  query?: Record<string, QueryValue>
  signal?: AbortSignal
}

// Same-origin by default ("/api/..."): the Vite dev server and the FastAPI server both serve the app and the API.
const BASE = ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '').replace(/\/$/, '')

let tokenProvider: () => string | null = () => null
let unauthorizedHandler: (() => void) | undefined

/** Wires the HTTP layer to the signed-in session (called once by the AuthProvider). */
export function configureHttp(config: { getToken: () => string | null; onUnauthorized?: () => void }): void {
  tokenProvider = config.getToken
  unauthorizedHandler = config.onUnauthorized
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const url = `${BASE}${path}`
  if (!query) return url
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value))
  }
  const qs = params.toString()
  return qs ? `${url}?${qs}` : url
}

async function parseError(response: Response): Promise<ApiError> {
  let body: Record<string, unknown> = {}
  try {
    body = (await response.json()) as Record<string, unknown>
  } catch {
    /* not JSON (for example a proxy error page) */
  }
  const { detail, code, fields, ...extra } = body
  const message =
    typeof detail === 'string' && detail
      ? detail
      : response.status === 404
        ? 'Not found.'
        : `The server answered with an error (${response.status}).`
  return new ApiError(
    response.status,
    typeof code === 'string' ? code : 'http_error',
    message,
    (fields as Record<string, string> | undefined) ?? {},
    extra,
  )
}

async function send(path: string, options: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = tokenProvider()
  if (token) headers.Authorization = `Bearer ${token}`
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'

  let response: Response
  try {
    response = await fetch(buildUrl(path, options.query), {
      method: options.method ?? 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    })
  } catch (error) {
    if (isAbort(error)) throw error
    throw new ApiError(0, 'network_error', 'Cannot reach the server. Check your connection and that the backend is running.')
  }
  if (!response.ok) {
    const error = await parseError(response)
    if (response.status === 401 && token && (error.code === 'invalid_token' || error.code === 'not_authenticated')) {
      unauthorizedHandler?.()
    }
    throw error
  }
  return response
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await send(path, options)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export interface BlobResult {
  blob: Blob
  filename: string | null
}

/** Fetch a binary file (image / PDF). The Authorization header is why images are not plain <img src>. */
export async function requestBlob(path: string, options: RequestOptions = {}): Promise<BlobResult> {
  const response = await send(path, options)
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const match = /filename="?([^";]+)"?/i.exec(disposition)
  return { blob: await response.blob(), filename: match?.[1] ?? null }
}
