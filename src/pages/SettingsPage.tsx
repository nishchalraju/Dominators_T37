import { LogOut } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { SelectField } from '@/components/ui/FormControls'
import { PageHeader } from '@/components/ui/PageHeader'
import { useAuth } from '@/hooks/auth-context'
import { useMeta } from '@/hooks/meta-context'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'
import { usePreferences } from '@/hooks/usePreferences'
import type { EngineChoice, Language } from '@/types/api'
import { formatDateTime, LANGUAGE_NAMES, REVIEW_LABELS } from '@/utils/format'

export function SettingsPage() {
  useDocumentTitle('Settings')
  const { user, logout } = useAuth()
  const { meta } = useMeta()
  const prefs = usePreferences()

  return (
    <>
      <PageHeader title="Settings" description="Your account, remembered defaults and information about this installation." />
      <div className="grid gap-6 xl:grid-cols-2">
        <Card aria-labelledby="account-title">
          <CardHeader id="account-title" title="Account" />
          <CardBody className="flex flex-col gap-4">
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              <div><dt className="text-xs text-subtle uppercase">Username</dt><dd className="text-ink">{user?.username}</dd></div>
              <div><dt className="text-xs text-subtle uppercase">Display name</dt><dd className="text-ink">{user?.display_name ?? '—'}</dd></div>
              <div><dt className="text-xs text-subtle uppercase">Role</dt><dd><Badge tone={user?.role === 'admin' ? 'accent' : 'neutral'}>{user?.role === 'admin' ? 'Administrator' : 'Investigator'}</Badge></dd></div>
              <div><dt className="text-xs text-subtle uppercase">Account created</dt><dd className="text-ink">{formatDateTime(user?.created_at)}</dd></div>
            </dl>
            <p className="text-sm text-muted">Administrators can run dataset inspections and parser evaluations and see every investigator’s cases. Your password is stored only as a salted hash on the server.</p>
            <div><Button icon={LogOut} onClick={logout}>Sign out</Button></div>
          </CardBody>
        </Card>

        <Card aria-labelledby="prefs-title">
          <CardHeader id="prefs-title" title="Defaults" description="Stored in this browser only." />
          <CardBody className="flex flex-col gap-4">
            <SelectField label="Default sketch engine" value={prefs.engine} onChange={(e) => prefs.setEngine(e.target.value as EngineChoice)} hint="If the AI engine is not set up, the forms say so and offer the schematic engine; nothing is switched silently.">
              <option value="schematic">Schematic composite (rule-based, not AI)</option>
              <option value="ai">AI engine</option>
            </SelectField>
            <SelectField label="Default language for descriptions and instructions" value={prefs.language} onChange={(e) => prefs.setLanguage(e.target.value as Language)}>
              {(['en', 'kn', 'hi'] as const).map((code) => <option key={code} value={code}>{LANGUAGE_NAMES[code]}</option>)}
            </SelectField>
            <p className="text-sm text-muted">Engine status and setup steps are on <Link to="/datasets" className="inline-link text-accent hover:text-accent-strong">Dataset and AI Evaluation</Link>.</p>
          </CardBody>
        </Card>

        <Card aria-labelledby="use-title" className="xl:col-span-2">
          <CardHeader id="use-title" title="Responsible use" description="You accepted this when you created your account." />
          <CardBody>
            <ul className="list-disc space-y-2 pl-5 text-sm text-muted">
              {(meta?.disclaimers.responsible_use ?? []).map((line) => <li key={line}>{line}</li>)}
            </ul>
          </CardBody>
        </Card>

        <Card aria-labelledby="sys-title">
          <CardHeader id="sys-title" title="About this installation" />
          <CardBody>
            <dl className="grid gap-3 text-sm sm:grid-cols-2">
              <div><dt className="text-xs text-subtle uppercase">Application</dt><dd className="text-ink">{meta?.app.name} {meta?.app.version}</dd></div>
              <div><dt className="text-xs text-subtle uppercase">Attribute vocabulary</dt><dd className="text-ink">version {meta?.vocabulary_version ?? '—'}</dd></div>
              <div className="sm:col-span-2"><dt className="text-xs text-subtle uppercase">Description parser</dt><dd className="text-ink">{meta?.parser.name} {meta?.parser.version}: a rule-based parser, not a trained model</dd></div>
              <div className="sm:col-span-2">
                <dt className="mb-1 text-xs text-subtle uppercase">Language word lists</dt>
                <dd className="flex flex-wrap gap-2">
                  {Object.entries(meta?.parser.lexicon_status ?? {}).map(([code, status]) => (
                    <Badge key={code} tone={status === 'unreviewed' ? 'warn' : 'neutral'}>{LANGUAGE_NAMES[code] ?? code}: {REVIEW_LABELS[status] ?? status}</Badge>
                  ))}
                </dd>
              </div>
            </dl>
          </CardBody>
        </Card>

        <Card aria-labelledby="priv-title">
          <CardHeader id="priv-title" title="Privacy and permissions" />
          <CardBody>
            <ul className="list-disc space-y-2 pl-5 text-sm text-muted">
              <li>This application never asks for your camera, microphone or location, and the server tells the browser to refuse them.</li>
              <li>No photographs are uploaded or processed. Sketches are drawn from attributes you choose.</li>
              <li>Sign-in uses a token kept in this browser; signing out removes it. Passwords are never kept in the browser.</li>
              <li>Face recognition, matching and suspect search are not part of this system and are not planned.</li>
            </ul>
          </CardBody>
        </Card>
      </div>
    </>
  )
}
