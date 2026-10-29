import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { ActiveCaseContext, type ActiveCaseState } from '@/hooks/active-case-context'
import { useAuth } from '@/hooks/auth-context'
import { api } from '@/services/api'
import { KEYS, safeStorage } from '@/services/storage'
import type { CaseDetail } from '@/types/api'
import { ApiError, isAbort } from '@/utils/errors'

/**
 * Remembers which case the investigator is working on. The id is kept in storage so it survives a reload and is
 * shared by the header, the Sketch Workspace and Reports. Mount it with `key={user.id}` so a different user
 * always starts with a clean slate.
 */
export function ActiveCaseProvider({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const [activeCaseId, setId] = useState<string | null>(() => safeStorage.get(KEYS.activeCase))
  const [loaded, setLoaded] = useState<CaseDetail | null>(null)
  const [failedFor, setFailedFor] = useState<string | null>(null)
  const [tick, setTick] = useState(0)

  const clearCase = useCallback(() => {
    safeStorage.remove(KEYS.activeCase)
    setId(null)
    setLoaded(null)
  }, [])

  const selectCase = useCallback((caseId: string) => {
    safeStorage.set(KEYS.activeCase, caseId)
    setId(caseId)
  }, [])

  useEffect(() => {
    if (status !== 'authenticated' || !activeCaseId) return
    const controller = new AbortController()
    api
      .getCase(activeCaseId, { signal: controller.signal })
      .then((detail) => {
        if (!controller.signal.aborted) setLoaded(detail)
      })
      .catch((error: unknown) => {
        if (isAbort(error) || controller.signal.aborted) return
        // The case was deleted, or is not ours any more: forget it instead of showing a broken state.
        if (error instanceof ApiError && error.status === 404) clearCase()
        else setFailedFor(activeCaseId)
      })
    return () => controller.abort()
  }, [status, activeCaseId, tick, clearCase])

  const authenticated = status === 'authenticated'
  const activeCase = authenticated && loaded && loaded.case_id === activeCaseId ? loaded : null
  const loading = authenticated && !!activeCaseId && !activeCase && failedFor !== activeCaseId

  const value = useMemo<ActiveCaseState>(
    () => ({
      activeCaseId: authenticated ? activeCaseId : null,
      activeCase,
      loading,
      selectCase,
      clearCase,
      refresh: () => setTick((t) => t + 1),
    }),
    [authenticated, activeCaseId, activeCase, loading, selectCase, clearCase],
  )
  return <ActiveCaseContext value={value}>{children}</ActiveCaseContext>
}
