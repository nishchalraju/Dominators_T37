import { Cpu, Sparkles } from 'lucide-react'
import { Badge } from './ui/Badge'

/** The most important label in the app: was this picture made by an AI model or drawn by fixed rules? */
export function EngineBadge({ isAi, className = '' }: { isAi: boolean; className?: string }) {
  return isAi ? (
    <Badge tone="warn" className={className}>
      <Sparkles className="size-3" aria-hidden="true" />
      AI-generated
    </Badge>
  ) : (
    <Badge tone="accent" className={className}>
      <Cpu className="size-3" aria-hidden="true" />
      Schematic · not AI
    </Badge>
  )
}
