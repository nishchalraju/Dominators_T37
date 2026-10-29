import { afterEach, describe, expect, it, vi } from 'vitest'
import { safeStorage } from './storage'

afterEach(() => vi.restoreAllMocks())

describe('safeStorage', () => {
  it('stores and removes values normally', () => {
    safeStorage.set('k1', 'v')
    expect(safeStorage.get('k1')).toBe('v')
    safeStorage.remove('k1')
    expect(safeStorage.get('k1')).toBeNull()
  })

  it('keeps working in memory when the browser blocks storage', () => {
    const blocked = () => {
      throw new DOMException('blocked', 'SecurityError')
    }
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(blocked)
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(blocked)
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(blocked)
    expect(() => safeStorage.set('k2', 'in-memory')).not.toThrow()
    expect(safeStorage.get('k2')).toBe('in-memory')
    safeStorage.remove('k2')
    expect(safeStorage.get('k2')).toBeNull()
  })
})
