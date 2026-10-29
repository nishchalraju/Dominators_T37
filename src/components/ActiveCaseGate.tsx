import { FolderOpen } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useActiveCase } from '@/hooks/active-case-context'
import type { CaseDetail } from '@/types/api'
import { CaseChooser } from './CaseChooser'
import { Card, CardBody, CardHeader } from './ui/Card'
import { LoadingBlock } from './ui/Feedback'

/** Renders its children only when a case is selected; otherwise asks the investigator to choose one. */
export function ActiveCaseGate({ purpose, children }: { purpose: string; children: (activeCase: CaseDetail) => ReactNode }) {
  const { activeCase, activeCaseId, loading } = useActiveCase()
  if (activeCase) return <>{children(activeCase)}</>
  if (activeCaseId && loading) return <LoadingBlock label="Loading the selected case" />
  return (
    <Card>
      <CardHeader
        title={`Choose a case to ${purpose}`}
        description="The case you select stays selected on the Sketch Workspace and Reports pages."
        actions={
          <Link to="/investigations/new" className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-line-strong bg-raised px-3 text-sm text-ink hover:border-accent/60">
            <FolderOpen className="size-4" aria-hidden="true" /> New investigation
          </Link>
        }
      />
      <CardBody>
        <CaseChooser />
      </CardBody>
    </Card>
  )
}
