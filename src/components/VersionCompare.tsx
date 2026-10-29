import { X } from 'lucide-react'
import { useMeta } from '@/hooks/meta-context'
import type { SketchVersion } from '@/types/api'
import { formatDateTime } from '@/utils/format'
import { AuthImage } from './AuthImage'
import { EngineBadge } from './EngineBadge'
import { Button } from './ui/Button'
import { Card, CardBody, CardHeader } from './ui/Card'

function Side({ version }: { version: SketchVersion }) {
  return (
    <figure className="flex min-w-0 flex-col gap-2">
      <AuthImage src={version.image_url} alt={`Sketch version ${version.version_number}`} className="aspect-square w-full rounded-lg bg-raised object-contain" />
      <figcaption className="flex flex-col gap-1 text-sm">
        <span className="flex flex-wrap items-center gap-2">
          <strong className="text-ink">Version {version.version_number}</strong>
          <EngineBadge isAi={version.is_ai_generated} />
        </span>
        <span className="witness-text text-muted">{version.kind === 'initial' ? 'Initial sketch' : `Instruction: “${version.instruction}”`}</span>
        <time className="text-xs text-subtle" dateTime={version.created_at}>
          {formatDateTime(version.created_at)}
        </time>
      </figcaption>
    </figure>
  )
}

/** Two versions side by side, plus a table of exactly which attributes differ between them. */
export function VersionCompare({ left, right, onClose }: { left: SketchVersion; right: SketchVersion; onClose: () => void }) {
  const { meta, valueLabel } = useMeta()
  const rows = (meta?.attributes ?? []).map((a) => ({ key: a.key, label: a.label, a: left.attributes[a.key] ?? null, b: right.attributes[a.key] ?? null }))
  const different = rows.filter((r) => r.a !== r.b)

  return (
    <Card aria-labelledby="compare-title">
      <CardHeader
        id="compare-title"
        title={`Comparing version ${left.version_number} and version ${right.version_number}`}
        description={different.length === 0 ? 'The structured attributes are identical (the images can still differ in detail).' : `${different.length} ${different.length === 1 ? 'attribute differs' : 'attributes differ'}.`}
        actions={
          <Button size="sm" icon={X} onClick={onClose}>
            Close comparison
          </Button>
        }
      />
      <CardBody>
        <div className="grid gap-6 md:grid-cols-2">
          <Side version={left} />
          <Side version={right} />
        </div>
        <div className="mt-5 overflow-x-auto rounded-lg border border-line">
          <table className="w-full min-w-[28rem] text-left text-sm">
            <caption className="sr-only">Attribute values of the two versions; differing rows are marked</caption>
            <thead className="bg-raised text-xs text-muted uppercase">
              <tr>
                <th scope="col" className="px-3 py-2 font-medium">Attribute</th>
                <th scope="col" className="px-3 py-2 font-medium">Version {left.version_number}</th>
                <th scope="col" className="px-3 py-2 font-medium">Version {right.version_number}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map((r) => (
                <tr key={r.key} className={r.a !== r.b ? 'bg-accent/5' : ''}>
                  <th scope="row" className="px-3 py-2 font-medium text-ink">
                    {r.label}
                    {r.a !== r.b ? <span className="ml-2 text-xs font-normal text-accent">changed</span> : null}
                  </th>
                  <td className="px-3 py-2 text-muted">{valueLabel(r.key, r.a)}</td>
                  <td className="px-3 py-2 text-muted">{valueLabel(r.key, r.b)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardBody>
    </Card>
  )
}
