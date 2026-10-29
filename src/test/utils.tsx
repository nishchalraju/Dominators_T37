import { render, type RenderResult } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import { App } from '@/App'
import { AuthProvider } from '@/components/providers/AuthProvider'
import { KeyedActiveCase } from '@/components/providers/KeyedActiveCase'
import { MetaProvider } from '@/components/providers/MetaProvider'
import { ToastProvider } from '@/components/providers/ToastProvider'
import { configureHttp } from '@/services/http'
import { KEYS } from '@/services/storage'
import type { User } from '@/types/api'
import { ADMIN, META } from './fixtures'

// ---------------------------------------------------------------------------------------- fetch stand-in
export interface RecordedCall {
  method: string
  path: string
  search: string
  body: unknown
  headers: Headers
}
type Handler = unknown | ((call: RecordedCall) => unknown)

/** Build a JSON Response. */
export const json = (body: unknown, status = 200, headers: Record<string, string> = {}) =>
  new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } })

/** A backend-style error body: {detail, code, ...extra}. */
export const apiError = (status: number, code: string, detail: string, extra: Record<string, unknown> = {}) => json({ detail, code, ...extra }, status)

const compile = (key: string) => {
  const [method, ...rest] = key.split(' ')
  const pattern = new RegExp('^' + rest.join(' ').replace(/:[A-Za-z_]+/g, '[^/]+') + '$')
  return { method, pattern }
}

/**
 * Replaces fetch with a stand-in that answers from `routes` ("GET /api/cases/:id" -> body or function).
 * Used only in tests. Any request without a route fails loudly so tests cannot silently depend on the network.
 */
export function mockFetch(routes: Record<string, Handler>) {
  const table = Object.entries(routes).map(([key, handler]) => ({ ...compile(key), handler }))
  const calls: RecordedCall[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === 'string' ? input : input.toString(), 'http://localhost')
    const method = (init?.method ?? 'GET').toUpperCase()
    let body: unknown
    try {
      body = init?.body ? JSON.parse(String(init.body)) : undefined
    } catch {
      body = init?.body
    }
    const call: RecordedCall = { method, path: url.pathname, search: url.search, body, headers: new Headers(init?.headers) }
    calls.push(call)
    const entry = table.find((t) => t.method === method && t.pattern.test(url.pathname))
    if (!entry) return json({ detail: `No test route for ${method} ${url.pathname}`, code: 'test_unrouted' }, 599)
    const result = typeof entry.handler === 'function' ? await (entry.handler as (c: RecordedCall) => unknown)(call) : entry.handler
    return result instanceof Response ? result : json(result)
  })
  vi.stubGlobal('fetch', fetchMock)
  return { calls, fetchMock, called: (method: string, path: RegExp | string) => calls.filter((c) => c.method === method && (typeof path === 'string' ? c.path === path : path.test(c.path))) }
}

// ---------------------------------------------------------------------------------------- rendering
/** Same provider stack as main.tsx, with an in-memory router. */
export function renderWithProviders(ui: ReactElement, { route = '/', signedInAs }: { route?: string; signedInAs?: User } = {}): RenderResult {
  if (signedInAs) window.localStorage.setItem(KEYS.token, 'test-token')
  return render(
    <MemoryRouter initialEntries={[route]}>
      <ToastProvider>
        <MetaProvider>
          <AuthProvider>
            <KeyedActiveCase>{ui}</KeyedActiveCase>
          </AuthProvider>
        </MetaProvider>
      </ToastProvider>
    </MemoryRouter>,
  )
}

/** Renders the whole app on `route`. */
export function renderApp(route = '/', signedInAs?: User): RenderResult {
  return renderWithProviders(<App />, { route, signedInAs })
}

/** Renders one page component under a route pattern (for pages that read URL parameters). */
export function renderRoute(pattern: string, element: ReactElement, url: string, signedInAs: User = ADMIN): RenderResult {
  return renderWithProviders(
    <Routes>
      <Route path={pattern} element={element} />
    </Routes>,
    { route: url, signedInAs },
  )
}

/** The routes almost every signed-in test needs. */
export const baseRoutes = (user: User = ADMIN): Record<string, Handler> => ({
  'GET /api/meta/attributes': META,
  'GET /api/auth/me': user,
})

export function resetHttp() {
  configureHttp({ getToken: () => null })
}
