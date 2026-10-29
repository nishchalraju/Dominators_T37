import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/auth-context'
import { LoadingBlock } from './ui/Feedback'

/** Routes inside this guard need a signed-in user; everyone else is sent to the login page. */
export function RequireAuth() {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'loading') {
    return (
      <div className="grid min-h-screen place-items-center">
        <LoadingBlock label="Checking your session" />
      </div>
    )
  }
  if (status === 'anonymous') return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  return <Outlet />
}
