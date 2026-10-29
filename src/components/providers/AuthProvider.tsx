import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { AuthContext, type AuthState } from '@/hooks/auth-context'
import { api } from '@/services/api'
import { configureHttp } from '@/services/http'
import { KEYS, safeStorage } from '@/services/storage'
import type { TokenResponse, User } from '@/types/api'

/**
 * Keeps the signed-in user. The access token lives in localStorage (or memory if storage is blocked)
 * and is attached to every request by the HTTP layer. No password is ever stored in the browser.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [initialToken] = useState(() => safeStorage.get(KEYS.token))
  const tokenRef = useRef<string | null>(initialToken)
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<AuthState['status']>(initialToken ? 'loading' : 'anonymous')
  const [notice, setNotice] = useState<string | null>(null)

  const signOut = useCallback((reason?: string) => {
    tokenRef.current = null
    safeStorage.remove(KEYS.token)
    safeStorage.remove(KEYS.activeCase)
    setUser(null)
    setStatus('anonymous')
    setNotice(reason ?? null)
  }, [])

  useEffect(() => {
    configureHttp({
      getToken: () => tokenRef.current,
      onUnauthorized: () => signOut('Your session has expired. Please sign in again.'),
    })
  }, [signOut])

  useEffect(() => {
    if (!tokenRef.current) return
    const controller = new AbortController()
    api
      .me({ signal: controller.signal })
      .then((me) => {
        setUser(me)
        setStatus('authenticated')
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        // A network failure is not a reason to throw the session away; anything else is.
        if (error instanceof Error && 'status' in error && (error as { status: number }).status !== 0) signOut()
        else setStatus('anonymous')
      })
    return () => controller.abort()
  }, [signOut])

  const accept = useCallback((result: TokenResponse) => {
    tokenRef.current = result.access_token
    safeStorage.set(KEYS.token, result.access_token)
    setUser(result.user)
    setStatus('authenticated')
    setNotice(null)
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      status,
      user,
      notice,
      login: async (username, password) => accept(await api.login({ username, password })),
      register: async (input) => accept(await api.register({ ...input, acknowledge_responsible_use: true })),
      logout: () => signOut(),
      clearNotice: () => setNotice(null),
    }),
    [status, user, notice, accept, signOut],
  )
  return <AuthContext value={value}>{children}</AuthContext>
}
