import { useCallback, useEffect, useState } from 'react'

import { ApiError } from './api'

export interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

/**
 * Minimal fetch lifecycle for page-level data: one in-flight request per
 * mount, cancelled on unmount, with a friendly message for API failures.
 */
export function useApi<T>(loader: () => Promise<T>, deps: unknown[] = []): AsyncState<T> & {
  reload: () => void
} {
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: true, error: null })
  const [nonce, setNonce] = useState(0)

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(loader, deps)

  useEffect(() => {
    let active = true
    setState((prev) => ({ ...prev, loading: true, error: null }))
    run()
      .then((data) => {
        if (active) setState({ data, loading: false, error: null })
      })
      .catch((error: unknown) => {
        if (!active) return
        const message =
          error instanceof ApiError ? error.message : 'Something went wrong loading this page.'
        setState({ data: null, loading: false, error: message })
      })
    return () => {
      active = false
    }
  }, [run, nonce])

  const reload = useCallback(() => setNonce((n) => n + 1), [])

  return { ...state, reload }
}
