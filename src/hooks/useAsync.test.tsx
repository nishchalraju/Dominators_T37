import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useAsync } from './useAsync'

describe('useAsync', () => {
  it('loads data and reports loading and error states', async () => {
    const loader = vi.fn().mockResolvedValueOnce('first')
    const { result } = renderHook(() => useAsync(() => loader(), []))
    expect(result.current.loading).toBe(true)
    await waitFor(() => expect(result.current.data).toBe('first'))
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('exposes the error and keeps previously loaded data on reload failure', async () => {
    const loader = vi.fn().mockResolvedValueOnce('ok').mockRejectedValueOnce(new Error('boom'))
    const { result } = renderHook(() => useAsync(() => loader(), []))
    await waitFor(() => expect(result.current.data).toBe('ok'))
    act(() => result.current.reload())
    await waitFor(() => expect(result.current.error).toBeInstanceOf(Error))
    expect(result.current.data).toBe('ok') // no flash of empty content
  })

  it('reloads when the inputs change and ignores an older, slower answer', async () => {
    let resolveSlow: (v: string) => void = () => undefined
    const loader = vi.fn((id: string) => (id === 'slow' ? new Promise<string>((r) => (resolveSlow = r)) : Promise.resolve(id)))
    const { result, rerender } = renderHook(({ id }) => useAsync(() => loader(id), [id]), { initialProps: { id: 'slow' } })
    rerender({ id: 'fast' })
    await waitFor(() => expect(result.current.data).toBe('fast'))
    await act(async () => resolveSlow('OLD'))
    expect(result.current.data).toBe('fast')
  })

  it('does nothing while disabled', () => {
    const loader = vi.fn()
    const { result } = renderHook(() => useAsync(loader, [], { enabled: false }))
    expect(loader).not.toHaveBeenCalled()
    expect(result.current.loading).toBe(false)
  })
})
