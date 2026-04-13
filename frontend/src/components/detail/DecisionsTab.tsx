import * as Collapsible from '@radix-ui/react-collapsible'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import type { Decision } from '../../types/api'

interface DecisionsTabProps {
  decisions: Decision[]
}

function DecisionCard({ decision }: { decision: Decision }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="bg-[#181825] border border-[#313244] rounded-lg p-4">
      <p className="text-gray-100 font-medium text-sm leading-relaxed mb-2">
        {decision.description}
      </p>

      {decision.participants && decision.participants.length > 0 && (
        <p className="text-xs text-[#6c7086] mb-2">
          Participants: {decision.participants.join(', ')}
        </p>
      )}

      {decision.rationale && (
        <p className="text-sm text-gray-400 leading-relaxed mb-3">{decision.rationale}</p>
      )}

      {decision.source_quote && (
        <Collapsible.Root open={open} onOpenChange={setOpen}>
          <Collapsible.Trigger className="flex items-center gap-1.5 text-xs text-[#89b4fa]/80 hover:text-[#89b4fa] transition-colors">
            {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            Source Quote
          </Collapsible.Trigger>
          <Collapsible.Content className="mt-2 pl-4 border-l border-[#313244]">
            <p className="text-xs text-[#6c7086] italic leading-relaxed">
              &ldquo;{decision.source_quote}&rdquo;
            </p>
          </Collapsible.Content>
        </Collapsible.Root>
      )}
    </div>
  )
}

export function DecisionsTab({ decisions }: DecisionsTabProps) {
  if (decisions.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-[#6c7086] text-sm">
        No decisions recorded
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {decisions.map((d) => (
        <DecisionCard key={d.id} decision={d} />
      ))}
    </div>
  )
}
