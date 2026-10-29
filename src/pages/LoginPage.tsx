import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Notice } from '@/components/ui/Feedback'
import { TextField } from '@/components/ui/FormControls'
import { useAuth } from '@/hooks/auth-context'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { AuthLayout } from '@/layouts/AuthLayout'
import { errorMessage } from '@/utils/errors'

export function LoginPage() {
  useDocumentTitle('Sign in')
  const { status, login, notice, clearNotice } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (status === 'authenticated') return <Navigate to={from} replace />

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    clearNotice()
    if (!username.trim() || !password) {
      setError('Enter your username and password.')
      return
    }
    setBusy(true)
    try {
      await login(username.trim(), password)
      navigate(from, { replace: true })
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title="Sign in" subtitle="Use your investigator account to open your cases.">
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {notice ? <Notice tone="warn">{notice}</Notice> : null}
        {error ? <Notice tone="danger">{error}</Notice> : null}
        <TextField label="Username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" autoFocus required />
        <TextField label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        <Button type="submit" variant="primary" loading={busy}>
          Sign in
        </Button>
        <p className="text-sm text-muted">
          No account yet?{' '}
          <Link to="/register" className="inline-link text-accent hover:text-accent-strong">
            Create one
          </Link>
          . The first account created on a new installation becomes the administrator.
        </p>
      </form>
    </AuthLayout>
  )
}
