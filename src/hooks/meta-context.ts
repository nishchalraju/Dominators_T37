import { createContext, useContext } from 'react'
import type { AttributeMeta, Meta } from '@/types/api'

export interface MetaState {
  meta: Meta | null
  loading: boolean
  error: string | null
  retry: () => void
  attribute: (key: string) => AttributeMeta | undefined
  attributeLabel: (key: string) => string
  /** Human label of a controlled value; "Not specified" for empty. */
  valueLabel: (key: string, value: string | null | undefined) => string
}

export const MetaContext = createContext<MetaState | null>(null)

export function useMeta(): MetaState {
  const value = useContext(MetaContext)
  if (!value) throw new Error('useMeta must be used inside <MetaProvider>')
  return value
}
