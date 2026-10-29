import { useCallback, useEffect, useState, type DependencyList } from 'react'
import { isAbort } from '@/utils/errors'

interface AsyncState<T> {
  data: T | undefined
  error: unknown
  loading: boolean
}

/**
 * Runs an async loader whenever `deps` change and tracks loading / error / data.
 * The request is cancelled when the component unmounts or the inputs change, so a slow
 * old answer can never overwrite a newer one. Previous data stays visible while reloading.
 */
export function useAsync<T>(loader: (signal: AbortSignal) => Promise<T>, deps: DependencyList, options: { enabled?: boolean } = {}) {
  const enabled = options.enabled ?? true
  const [state, setState] = useState<AsyncState<T>>({ data: undefined, error: null, loading: enabled })
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!enabled) {
      setState((s) => ({ ...s, loading: false }))
      return
    }
    const controller = new AbortController()
    setState((s) => ({ ...s, loading: true, error: null }))
    loader(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ data, error: null, loading: false })
      })
      .catch((error: unknown) => {
        if (isAbort(error) || controller.signal.aborted) return
        setState((s) => ({ ...s, error, loading: false }))
      })
    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `loader` is intentionally re-created each render
  }, [...deps, tick, enabled])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  const setData = useCallback((data: T) => setState((s) => ({ ...s, data })), [])
  return { ...state, reload, setData }
}
