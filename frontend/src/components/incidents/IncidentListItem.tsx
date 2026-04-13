import { Loader2 } from 'lucide-react'
import { SeverityBadge } from './SeverityBadge'
import { formatDate } from '../../lib/utils'
import type { IncidentListItem as IncidentListItemType } from '../../types/api'

interface IncidentListItemProps {
  incident: IncidentListItemType
  isSelected: boolean
  onClick: () => void
}

export function IncidentListItem({ incident, isSelected, onClick }: IncidentListItemProps) {
  const isProcessing = ['pending', 'analyzing', 'embedding'].includes(incident.processing_status)

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-3 rounded-lg transition-colors ${
        isSelected
          ? 'bg-[#89b4fa]/10 border border-[#89b4fa]/30'
          : 'hover:bg-[#2a2a3d] border border-transparent'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <span className="text-xs font-medium text-gray-200 leading-tight line-clamp-2 flex-1">
          {incident.title}
        </span>
        <SeverityBadge severity={incident.severity} className="shrink-0" />
      </div>

      <div className="flex items-center gap-2">
        {isProcessing && (
          <Loader2 size={10} className="text-[#f9e2af] animate-spin shrink-0" />
        )}
        <span className="text-[10px] text-[#6c7086]">
          {incident.services_affected.length > 0
            ? incident.services_affected.slice(0, 2).join(', ')
            : 'No services'}
        </span>
        {incident.occurred_at && (
          <>
            <span className="text-[10px] text-[#45475a]">·</span>
            <span className="text-[10px] text-[#6c7086]">{formatDate(incident.occurred_at)}</span>
          </>
        )}
      </div>
    </button>
  )
}
