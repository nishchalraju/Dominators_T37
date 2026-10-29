import { createContext, useContext } from 'react'
import type { CaseDetail } from '@/types/api'

export interface ActiveCaseState {
  /** The case the investigator is working on. It stays selected across Workspace, Reports and the header. */
  activeCaseId: string | null
  activeCase: CaseDetail | null
  loading: boolean
  selectCase: (caseId: string) => void
  clearCase: () => void
  /** Re-read the case from the server (after adding a sketch, a note, ...). */
  refresh: () => void
}

export const ActiveCaseContext = createContext<ActiveCaseState | null>(null)

export function useActiveCase(): ActiveCaseState {
  const value = useContext(ActiveCaseContext)
  if (!value) throw new Error('useActiveCase must be used inside <ActiveCaseProvider>')
  return value
}
