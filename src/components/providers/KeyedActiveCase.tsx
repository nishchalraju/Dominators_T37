import type { ReactNode } from 'react'
import { useAuth } from '@/hooks/auth-context'
import { ActiveCaseProvider } from './ActiveCaseProvider'

/** Gives every signed-in user their own ActiveCaseProvider, so nothing leaks from one account to the next. */
export function KeyedActiveCase({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  return <ActiveCaseProvider key={user?.id ?? 'anonymous'}>{children}</ActiveCaseProvider>
}
