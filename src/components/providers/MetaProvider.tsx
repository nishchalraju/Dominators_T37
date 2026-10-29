import { useCallback, useMemo, type ReactNode } from 'react'
import { MetaContext, type MetaState } from '@/hooks/meta-context'
import { useAsync } from '@/hooks/useAsync'
import { api } from '@/services/api'
import { errorMessage } from '@/utils/errors'

/** Loads the controlled vocabulary from the backend once, so forms can never offer a value the server would reject. */
export function MetaProvider({ children }: { children: ReactNode }) {
  const { data, error, loading, reload } = useAsync((signal) => api.meta({ signal }), [])
  const attribute = useCallback((key: string) => data?.attributes.find((a) => a.key === key), [data])

  const value = useMemo<MetaState>(
    () => ({
      meta: data ?? null,
      loading,
      error: error ? errorMessage(error, 'Could not load the vocabulary from the server.') : null,
      retry: reload,
      attribute,
      attributeLabel: (key) => attribute(key)?.label ?? key,
      valueLabel: (key, val) => (val ? (attribute(key)?.values.find((v) => v.value === val)?.label ?? val) : 'Not specified'),
    }),
    [data, loading, error, reload, attribute],
  )
  return <MetaContext value={value}>{children}</MetaContext>
}
