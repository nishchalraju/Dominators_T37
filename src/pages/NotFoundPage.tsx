import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/ui/Feedback'
import { useDocumentTitle } from '@/hooks/useDocumentTitle'

export function NotFoundPage() {
  useDocumentTitle('Page not found')
  return (
    <EmptyState title="This page does not exist" action={<Link to="/" className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-accent-ink">Go to the dashboard</Link>}>
      The address may be mistyped, or the page may have moved.
    </EmptyState>
  )
}
