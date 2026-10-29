import { createContext, useContext } from 'react'

export interface Toaster {
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
}

export const ToastContext = createContext<Toaster | null>(null)

export function useToast(): Toaster {
  const value = useContext(ToastContext)
  if (!value) throw new Error('useToast must be used inside <ToastProvider>')
  return value
}
