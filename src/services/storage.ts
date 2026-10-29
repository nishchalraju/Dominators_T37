/**
 * localStorage that never throws. Some environments (private windows, sandboxed iframes) block
 * storage; then values simply live in memory for the current page load instead of crashing the app.
 */
const memory = new Map<string, string>()

export const safeStorage = {
  get(key: string): string | null {
    try {
      return window.localStorage.getItem(key)
    } catch {
      return memory.get(key) ?? null
    }
  },
  set(key: string, value: string): void {
    try {
      window.localStorage.setItem(key, value)
    } catch {
      memory.set(key, value)
    }
  },
  remove(key: string): void {
    try {
      window.localStorage.removeItem(key)
    } catch {
      memory.delete(key)
    }
    memory.delete(key)
  },
}

export const KEYS = {
  token: 'sketchassist.token',
  activeCase: 'sketchassist.activeCase',
  engine: 'sketchassist.defaultEngine',
  language: 'sketchassist.defaultLanguage',
} as const
