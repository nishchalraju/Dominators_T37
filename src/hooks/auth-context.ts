import { createContext, useContext } from 'react'
import type { User } from '@/types/api'

export interface AuthState {
  status: 'loading' | 'authenticated' | 'anonymous'
  user: User | null
  /** Why the user was signed out (for example an expired session). Shown on the login page. */
  notice: string | null
  login: (username: string, password: string) => Promise<void>
  register: (input: { username: string; password: string; display_name?: string }) => Promise<void>
  logout: () => void
  clearNotice: () => void
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>')
  return value
}
