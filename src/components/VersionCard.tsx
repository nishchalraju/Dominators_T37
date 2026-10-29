import { Check, Download, GitCompare } from 'lucide-react'
import type { SketchVersion } from '@/types/api'
import { formatDateTime } from '@/utils/format'
import { AuthImage } from './AuthImage'
import { EngineBadge } from './EngineBadge'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'

interface Props {
  version: SketchVersion
  compared: boolean
  onToggleCompare: () => void
  onSelect: () => void
  onDownload: () => void
  selecting?: boolean
  downloading?: boolean
  readOnly?: boolean
}

/** One entry of the version history. Versions are never overwritten: every revision is a new card. */
export function VersionCard({ version, compared, onToggleCompare, onSelect, onDownload, selecting, downloading, readOnly }: Props) {
  return (
    <li className={`flex flex-col overflow-hidden rounded-xl border bg-surface ${version.is_selected ? 'border-accent/70' : 'border-line'}`}>
      <AuthImage src={version.thumbnail_url} alt={`Sketch version ${version.version_number}`} className="aspect-square w-full bg-raised object-cover" />
      <div className="flex flex-1 flex-col gap-2 p-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold text-ink">Version {version.version_number}</h3>
          {version.is_selected ? (
            <Badge tone="ok">
              <Check className="size-3" aria-hidden="true" /> Selected
            </Badge>
          ) : null}
          <EngineBadge isAi={version.is_ai_generated} />
        </div>
        <p className="witness-text text-xs text-muted">
          {version.kind === 'initial' ? 'Initial sketch' : `“${version.instruction}”`}
          {version.parent_version_number ? <span className="text-subtle"> · from version {version.parent_version_number}</span> : null}
        </p>
        <p className="mt-auto text-xs text-subtle">
          <time dateTime={version.created_at}>{formatDateTime(version.created_at)}</time>
        </p>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant={version.is_selected ? 'ghost' : 'secondary'} onClick={onSelect} disabled={version.is_selected || readOnly} loading={selecting}>
            {version.is_selected ? 'Selected for editing' : 'Select for editing'}
          </Button>
          <Button size="sm" icon={Download} onClick={onDownload} loading={downloading}>
            Download
          </Button>
          <label className="flex cursor-pointer items-center gap-1.5 rounded-lg px-2 text-xs text-muted hover:text-ink">
            <input type="checkbox" className="size-4 accent-cyan-400" checked={compared} onChange={onToggleCompare} />
            <GitCompare className="size-3.5" aria-hidden="true" /> Compare
            {' '}<span className="sr-only">version {version.version_number}</span>
          </label>
        </div>
      </div>
    </li>
  )
}
