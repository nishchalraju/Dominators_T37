import { CircleHelp, TriangleAlert } from 'lucide-react'
import { useMeta } from '@/hooks/meta-context'
import type { ParseResponse } from '@/types/api'
import { LANGUAGE_NAMES, REVIEW_LABELS } from '@/utils/format'
import { Badge } from './ui/Badge'
import { Notice } from './ui/Feedback'

/** Shows exactly what the parser understood (with the witness's own words), and what it did NOT. */
export function ParseResultPanel({ result }: { result: ParseResponse }) {
  const { attributeLabel, valueLabel } = useMeta()
  const understood = result.details.length

  return (
    <div className="flex flex-col gap-4">
      <Notice tone="info">{result.notice}</Notice>

      {result.warnings.length > 0 ? (
        <Notice tone="warn" title="Please check">
          <ul className="list-disc space-y-1 pl-4">
            {result.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </Notice>
      ) : null}

      <div>
        <h3 className="mb-2 text-sm font-semibold text-ink">
          Understood <span className="font-normal text-muted">({understood} {understood === 1 ? 'attribute' : 'attributes'})</span>
        </h3>
        {understood === 0 ? (
          <p className="text-sm text-muted">Nothing could be turned into an attribute. You can still choose values by hand below.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-line">
            <table className="w-full min-w-[34rem] text-left text-sm">
              <caption className="sr-only">Attributes read from the description, with the words that caused each one</caption>
              <thead className="bg-raised text-xs text-muted uppercase">
                <tr>
                  <th scope="col" className="px-3 py-2 font-medium">Attribute</th>
                  <th scope="col" className="px-3 py-2 font-medium">Estimate</th>
                  <th scope="col" className="px-3 py-2 font-medium">Your words</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {result.details.map((d) => (
                  <tr key={d.attribute}>
                    <th scope="row" className="px-3 py-2 font-medium text-ink">{attributeLabel(d.attribute)}</th>
                    <td className="px-3 py-2 text-accent">{valueLabel(d.attribute, d.value)}</td>
                    <td className="px-3 py-2">
                      <span className="witness-text text-ink">“{d.evidence}”</span>
                      <span className="ml-2 text-xs text-subtle">
                        {d.language === 'number' ? 'stated age' : `${LANGUAGE_NAMES[d.language] ?? d.language} word list`}
                        {d.match_type === 'negation' ? ' · negated' : d.match_type === 'inflected' ? ' · word ending matched' : d.match_type === 'pronoun' ? ' · pronoun only' : ''}
                      </span>
                      {d.note ? <p className="mt-0.5 text-xs text-warn">{d.note}</p> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {result.conflicts.length > 0 ? (
        <div>
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
            <TriangleAlert className="size-4 text-warn" aria-hidden="true" /> Conflicting statements — left empty
          </h3>
          <ul className="space-y-2">
            {result.conflicts.map((c) => (
              <li key={c.attribute} className="rounded-lg border border-warn/30 bg-warn/5 p-3 text-sm">
                <strong>{attributeLabel(c.attribute)}:</strong> {c.values.map((v) => valueLabel(c.attribute, v)).join(' vs ')}
                <span className="witness-text block text-muted">{c.evidence.map((e) => `“${e}”`).join('  ·  ')}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div>
        <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
          <CircleHelp className="size-4 text-muted" aria-hidden="true" />
          Not converted <span className="font-normal text-muted">({result.unrecognized.length})</span>
        </h3>
        {result.unrecognized.length === 0 ? (
          <p className="text-sm text-muted">Every part of the text was either understood or ignorable.</p>
        ) : (
          <ul className="space-y-1.5">
            {result.unrecognized.map((u) => (
              <li key={u.text} className="rounded-lg border border-line bg-bg px-3 py-2 text-sm">
                <span className="witness-text text-ink">“{u.text}”</span>
                <span className="block text-xs text-subtle">{u.reason}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs text-subtle">
        <span>
          Parser {result.parser_name} {result.parser_version}. Word lists:
        </span>
        {Object.entries(result.lexicon_status).map(([code, status]) => (
          <Badge key={code} tone={status === 'unreviewed' ? 'warn' : 'neutral'}>
            {LANGUAGE_NAMES[code] ?? code}: {REVIEW_LABELS[status] ?? status}
          </Badge>
        ))}
      </div>
    </div>
  )
}
