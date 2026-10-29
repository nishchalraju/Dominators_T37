import { Cpu, Sparkles } from 'lucide-react'
import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAsync } from '@/hooks/useAsync'
import { api } from '@/services/api'
import type { EngineChoice } from '@/types/api'
import { Badge } from './ui/Badge'
import { Notice, Skeleton } from './ui/Feedback'

interface Props {
  value: EngineChoice
  onChange: (value: EngineChoice) => void
  /** Show only the engines that make sense (revisions of an AI sketch cannot use the schematic engine). */
  disableSchematic?: boolean
  name?: string
}

/**
 * Chooses between the rule-based schematic engine and the AI engine. If the AI engine is not set up
 * the option is disabled and says why. The choice is never changed behind the user's back without a visible notice.
 */
export function EngineChooser({ value, onChange, disableSchematic = false, name = 'engine' }: Props) {
  const { data: engines, error, loading } = useAsync((signal) => api.engines({ signal }), [])
  const ai = (engines ?? []).filter((e) => e.is_ai)
  const readyAi = ai.find((e) => e.available)
  const loaded = engines !== undefined
  const aiBlocked = loaded && !readyAi

  useEffect(() => {
    if (aiBlocked && value === 'ai' && !disableSchematic) onChange('schematic')
  }, [aiBlocked, value, disableSchematic, onChange])

  if (loading && !engines) return <Skeleton className="h-28 w-full" />

  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="mb-1 text-sm font-medium text-ink">Sketch engine</legend>
      <label
        className={`flex gap-3 rounded-lg border p-3 ${value === 'schematic' ? 'border-accent/60 bg-accent/5' : 'border-line-strong'} ${disableSchematic ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
      >
        <input type="radio" name={name} className="mt-1 accent-cyan-400" checked={value === 'schematic'} disabled={disableSchematic} onChange={() => onChange('schematic')} />
        <span className="flex-1 text-sm">
          <span className="flex flex-wrap items-center gap-2 font-medium text-ink">
            <Cpu className="size-4 text-accent" aria-hidden="true" /> Schematic composite
            <Badge tone="accent">not AI</Badge>
            <Badge tone="ok">always available</Badge>
          </span>
          <span className="mt-1 block text-muted">A rule-based drawing made from the attribute values. Every attribute changes the picture. It is a generic diagram, not a likeness.</span>
        </span>
      </label>
      <label className={`flex gap-3 rounded-lg border p-3 ${value === 'ai' ? 'border-warn/60 bg-warn/5' : 'border-line-strong'} ${aiBlocked ? 'cursor-not-allowed opacity-70' : 'cursor-pointer'}`}>
        <input type="radio" name={name} className="mt-1 accent-cyan-400" checked={value === 'ai'} disabled={aiBlocked} onChange={() => onChange('ai')} />
        <span className="flex-1 text-sm">
          <span className="flex flex-wrap items-center gap-2 font-medium text-ink">
            <Sparkles className="size-4 text-warn" aria-hidden="true" /> AI engine
            <Badge tone="warn">AI-generated</Badge>
            {aiBlocked ? <Badge tone="danger">setup required</Badge> : readyAi ? <Badge tone="ok">configured</Badge> : null}
          </span>
          <span className="mt-1 block text-muted">
            {readyAi
              ? `Uses ${readyAi.label}${readyAi.models.generate ? ` (${readyAi.models.generate})` : ''}. It is configured but not yet verified until a first request succeeds. AI images can contain invented details.`
              : 'An AI image model. It needs credentials on the server.'}
          </span>
        </span>
      </label>
      {aiBlocked ? (
        <Notice tone="info" title="The AI engine is not set up on this server">
          No AI provider has credentials, so only the schematic engine can run. See the setup steps under{' '}
          <Link to="/datasets" className="inline-link text-accent hover:text-accent-strong">Dataset and AI Evaluation</Link>. Nothing is substituted silently.
        </Notice>
      ) : null}
      {error ? <Notice tone="warn">Could not read the engine status. The server will still refuse an engine that is not set up.</Notice> : null}
    </fieldset>
  )
}
