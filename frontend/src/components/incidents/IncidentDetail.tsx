import * as Tabs from '@radix-ui/react-tabs'
import { AlertTriangle, MessageSquare, Loader2 } from 'lucide-react'
import { useIncident } from '../../hooks/useIncident'
import { SeverityBadge } from './SeverityBadge'
import { PostmortemTab } from './PostmortemTab'
import { TimelineTab } from './TimelineTab'
import { IncidentActionItemsTab } from './IncidentActionItemsTab'
import { formatDate } from '../../lib/utils'

interface IncidentDetailProps {
  incidentId: string
  onOpenChat: (scope?: string) => void
}

const PROCESSING_STATUSES = ['pending', 'analyzing', 'embedding']

export function IncidentDetail({ incidentId, onOpenChat }: IncidentDetailProps) {
  const { data: incident, isLoading, error } = useIncident(incidentId)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={24} className="animate-spin text-[#6c7086]" />
      </div>
    )
  }

  if (error || !incident) {
    return (
      <div className="flex items-center justify-center h-full text-xs text-[#f38ba8]">
        Failed to load incident.
      </div>
    )
  }

  const isProcessing = PROCESSING_STATUSES.includes(incident.processing_status)

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {isProcessing && (
        <div className="mx-4 mt-3 rounded-lg bg-amber-900/30 border border-amber-700/40 p-3 shrink-0">
          <div className="flex items-center gap-2 mb-2">
            <Loader2 size={12} className="text-amber-400 animate-spin shrink-0" />
            <p className="text-xs text-amber-200">
              {incident.processing_status === 'analyzing'
                ? 'Analyzing incident with AI…'
                : incident.processing_status === 'embedding'
                ? 'Generating embeddings…'
                : 'Queued for analysis…'}
            </p>
          </div>
          <div className="w-full h-1 bg-amber-900/50 rounded-full overflow-hidden">
            <div className="h-full bg-amber-400 rounded-full progress-animate" />
          </div>
        </div>
      )}

      {incident.processing_status === 'failed' && (
        <div className="mx-4 mt-3 p-3 bg-[#f38ba8]/10 border border-[#f38ba8]/30 rounded-lg text-xs text-[#f38ba8]">
          Analysis failed: {incident.error_message || 'Unknown error'}
        </div>
      )}

      {/* Header */}
      <div className="px-4 pt-4 pb-3 border-b border-[#313244] shrink-0">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-start gap-2 min-w-0">
            <AlertTriangle size={16} className="text-[#f38ba8] shrink-0 mt-0.5" />
            <h2 className="text-sm font-semibold text-gray-100 leading-snug">{incident.title}</h2>
          </div>
          <SeverityBadge severity={incident.severity} className="shrink-0" />
        </div>

        <div className="flex items-center flex-wrap gap-3 text-[10px] text-[#6c7086] ml-6">
          {incident.services_affected.length > 0 && (
            <span>{incident.services_affected.join(', ')}</span>
          )}
          {incident.occurred_at && (
            <>
              <span className="text-[#45475a]">·</span>
              <span>{formatDate(incident.occurred_at)}</span>
            </>
          )}
          <span className="text-[#45475a]">·</span>
          <span className={`capitalize ${incident.status === 'resolved' || incident.status === 'closed' ? 'text-[#a6e3a1]' : 'text-[#f9e2af]'}`}>
            {incident.status}
          </span>
          {incident.airtable_record_id && (
            <>
              <span className="text-[#45475a]">·</span>
              <span className="px-1.5 py-0.5 rounded bg-[#89b4fa]/10 border border-[#89b4fa]/30 text-[#89b4fa]">
                Synced to Airtable
              </span>
            </>
          )}
        </div>

        <div className="flex gap-2 mt-3 ml-6">
          <button
            onClick={() => onOpenChat(`incident:${incident.id}`)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-medium text-[#6c7086] border border-[#313244] rounded-lg hover:bg-[#2a2a3d] hover:text-gray-300 transition-colors"
          >
            <MessageSquare size={11} />
            Ask about this incident
          </button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs.Root defaultValue="postmortem" className="flex flex-col flex-1 overflow-hidden">
        <Tabs.List className="flex border-b border-[#313244] px-4 shrink-0 overflow-x-auto">
          {[
            { value: 'postmortem', label: 'Postmortem' },
            { value: 'timeline', label: 'Timeline' },
            { value: 'actions', label: `Actions (${incident.action_items.length})` },
          ].map((tab) => (
            <Tabs.Trigger
              key={tab.value}
              value={tab.value}
              className="px-3 py-2.5 text-[11px] font-medium text-[#6c7086] border-b-2 border-transparent data-[state=active]:text-[#89b4fa] data-[state=active]:border-[#89b4fa] transition-colors whitespace-nowrap"
            >
              {tab.label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        <div className="flex-1 overflow-y-auto">
          <Tabs.Content value="postmortem">
            <PostmortemTab postmortem={incident.postmortem} />
          </Tabs.Content>
          <Tabs.Content value="timeline">
            <TimelineTab events={incident.timeline} />
          </Tabs.Content>
          <Tabs.Content value="actions">
            <IncidentActionItemsTab actionItems={incident.action_items} />
          </Tabs.Content>
        </div>
      </Tabs.Root>
    </div>
  )
}
