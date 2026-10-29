import { useCallback, useState } from 'react'
import { KEYS, safeStorage } from '@/services/storage'
import type { EngineChoice, Language } from '@/types/api'

/** Remembered defaults (stored in this browser only). */
export function usePreferences() {
  const [engine, setEngineState] = useState<EngineChoice>(() => (safeStorage.get(KEYS.engine) === 'ai' ? 'ai' : 'schematic'))
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = safeStorage.get(KEYS.language)
    return saved === 'kn' || saved === 'hi' ? saved : 'en'
  })
  const setEngine = useCallback((value: EngineChoice) => {
    safeStorage.set(KEYS.engine, value)
    setEngineState(value)
  }, [])
  const setLanguage = useCallback((value: Language) => {
    safeStorage.set(KEYS.language, value)
    setLanguageState(value)
  }, [])
  return { engine, setEngine, language, setLanguage }
}
