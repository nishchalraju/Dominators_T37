import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Notice } from '@/components/ui/Feedback'
import { CheckboxField, TextField } from '@/components/ui/FormControls'
import { useAuth } from '@/hooks/auth-context'
import { useMeta } from '@/hooks/meta-context'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { AuthLayout } from '@/layouts/AuthLayout'
import { errorMessage, fieldErrors } from '@/utils/errors'

export function RegisterPage() {
  useDocumentTitle('Create account')
  const { status, register } = useAuth()
  const { meta } = useMeta()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', displayName: '', password: '', confirm: '' })
  const [accepted, setAccepted] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (status === 'authenticated') return <Navigate to="/" replace />
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [key]: e.target.value }))

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const next: Record<string, string> = {}
    if (!/^[A-Za-z0-9_.-]{3,32}$/.test(form.username.trim())) next.username = 'Use 3-32 characters: letters, digits, underscore, dot or hyphen.'
    if (form.password.length < 10) next.password = 'Use at least 10 characters.'
    if (form.confirm !== form.password) next.confirm = 'The two passwords do not match.'
    if (!accepted) next.acknowledge_responsible_use = 'You must accept the responsible-use statement to continue.'
    setErrors(next)
    setFormError(null)
    if (Object.keys(next).length > 0) return
    setBusy(true)
    try {
      await register({ username: form.username.trim(), password: form.password, display_name: form.displayName.trim() || undefined })
      navigate('/', { replace: true })
    } catch (e) {
      const fields = fieldErrors(e)
      if (Object.keys(fields).length > 0) setErrors(fields)
      else setFormError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title="Create an account" subtitle="Accounts keep each investigator's cases separate.">
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {formError ? <Notice tone="danger">{formError}</Notice> : null}
        <TextField label="Username" value={form.username} onChange={set('username')} error={errors.username} autoComplete="username" required />
        <TextField label="Display name (optional)" value={form.displayName} onChange={set('displayName')} error={errors.display_name} autoComplete="name" />
        <TextField label="Password" type="password" value={form.password} onChange={set('password')} error={errors.password} hint="At least 10 characters." autoComplete="new-password" required />
        <TextField label="Repeat password" type="password" value={form.confirm} onChange={set('confirm')} error={errors.confirm} autoComplete="new-password" required />

        <fieldset className="rounded-lg border border-line bg-bg p-4">
          <legend className="px-1 text-sm font-semibold text-ink">Responsible use</legend>
          <ul className="mb-4 list-disc space-y-1.5 pl-5 text-sm text-muted">
            {(meta?.disclaimers.responsible_use ?? []).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <CheckboxField
            label="I have read this statement and will use SketchAssist AI accordingly."
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
            error={errors.acknowledge_responsible_use}
          />
        </fieldset>

        <Button type="submit" variant="primary" loading={busy}>
          Create account
        </Button>
        <p className="text-sm text-muted">
          Already registered?{' '}
          <Link to="/login" className="inline-link text-accent hover:text-accent-strong">
            Sign in
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
