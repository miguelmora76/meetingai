import * as Tabs from '@radix-ui/react-tabs'
import { Clock, Calendar, Users, MessageSquare, AlertTriangle } from 'lucide-react'
import { useMeeting } from '../../hooks/useMeeting'
import { formatDate, formatDuration } from '../../lib/utils'
import { StatusBadge } from './StatusBadge'
import { ProcessingBanner } from './ProcessingBanner'
import { SummaryTab } from '../detail/SummaryTab'
import { TranscriptTab } from '../detail/TranscriptTab'
import { ActionItemsTab } from '../detail/ActionItemsTab'
import { DecisionsTab } from '../detail/DecisionsTab'

interface MeetingDetailProps {
  meetingId: string
  onOpenChat: (meetingId: string) => void
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4 p-6">
      <div className="h-6 bg-[#313244] rounded w-2/3" />
      <div className="flex gap-3">
        <div className="h-4 bg-[#313244] rounded w-24" />
        <div className="h-4 bg-[#313244] rounded w-20" />
      </div>
      <div className="h-px bg-[#313244]" />
      <div className="space-y-2">
        <div className="h-4 bg-[#313244] rounded w-full" />
        <div className="h-4 bg-[#313244] rounded w-5/6" />
        <div className="h-4 bg-[#313244] rounded w-4/5" />
      </div>
    </div>
  )
}

export function MeetingDetail({ meetingId, onOpenChat }: MeetingDetailProps) {
  const { data: meeting, isLoading, error } = useMeeting(meetingId)

  if (isLoading) return <LoadingSkeleton />

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-center p-8">
        <AlertTriangle size={32} className="text-red-400" />
        <p className="text-sm text-red-400">Failed to load meeting</p>
        <p className="text-xs text-[#6c7086]">{error.message}</p>
      </div>
    )
  }

  if (!meeting) return null

  const isProcessing = meeting.status === 'processing' || meeting.status === 'uploaded'

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b border-[#313244] shrink-0">
        {isProcessing && <ProcessingBanner meetingTitle={meeting.title} />}

        <div className="flex items-start justify-between gap-4 mb-3">
          <h1 className="text-lg font-semibold text-gray-100 leading-tight">{meeting.title}</h1>
          <div className="flex items-center gap-2 shrink-0">
            <StatusBadge status={meeting.status} />
            <button
              onClick={() => onOpenChat(meetingId)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-[#89b4fa]/10 text-[#89b4fa] border border-[#89b4fa]/20 rounded-lg hover:bg-[#89b4fa]/20 transition-colors"
            >
              <MessageSquare size={13} />
              Ask about this meeting
            </button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 text-xs text-[#6c7086]">
          {(meeting.date ?? meeting.created_at) && (
            <span className="flex items-center gap-1.5">
              <Calendar size={13} />
              {formatDate(meeting.date ?? meeting.created_at)}
            </span>
          )}
          {meeting.duration_seconds != null && (
            <span className="flex items-center gap-1.5">
              <Clock size={13} />
              {formatDuration(meeting.duration_seconds)}
            </span>
          )}
        </div>

        {meeting.participants && meeting.participants.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <Users size={13} className="text-[#6c7086]" />
            {meeting.participants.map((p) => (
              <span
                key={p}
                className="px-2 py-0.5 bg-[#313244]/60 text-gray-300 text-xs rounded-full"
              >
                {p}
              </span>
            ))}
          </div>
        )}

        {meeting.status === 'failed' && meeting.error_message && (
          <div className="mt-3 flex items-center gap-2 text-xs text-red-400 bg-red-900/20 border border-red-800/40 rounded-lg px-3 py-2">
            <AlertTriangle size={13} />
            {meeting.error_message}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex-1 overflow-hidden">
        <Tabs.Root defaultValue="summary" className="flex flex-col h-full">
          <Tabs.List className="flex border-b border-[#313244] px-6 shrink-0">
            {['summary', 'transcript', 'actions', 'decisions'].map((tab) => (
              <Tabs.Trigger
                key={tab}
                value={tab}
                className="px-4 py-3 text-xs font-medium text-[#6c7086] hover:text-gray-300 transition-colors border-b-2 border-transparent data-[state=active]:border-[#89b4fa] data-[state=active]:text-[#89b4fa] capitalize"
              >
                {tab === 'actions' ? 'Action Items' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                {tab === 'actions' && meeting.action_items?.length > 0 && (
                  <span className="ml-1.5 bg-[#313244] text-[#6c7086] text-[10px] px-1.5 py-0.5 rounded-full">
                    {meeting.action_items.length}
                  </span>
                )}
                {tab === 'decisions' && meeting.decisions?.length > 0 && (
                  <span className="ml-1.5 bg-[#313244] text-[#6c7086] text-[10px] px-1.5 py-0.5 rounded-full">
                    {meeting.decisions.length}
                  </span>
                )}
              </Tabs.Trigger>
            ))}
          </Tabs.List>

          <div className="flex-1 overflow-y-auto">
            <Tabs.Content value="summary" className="p-6">
              <SummaryTab summary={meeting.summary} status={meeting.status} />
            </Tabs.Content>
            <Tabs.Content value="transcript" className="p-6">
              <TranscriptTab transcript={meeting.transcript} status={meeting.status} />
            </Tabs.Content>
            <Tabs.Content value="actions" className="p-6">
              <ActionItemsTab items={meeting.action_items ?? []} />
            </Tabs.Content>
            <Tabs.Content value="decisions" className="p-6">
              <DecisionsTab decisions={meeting.decisions ?? []} />
            </Tabs.Content>
          </div>
        </Tabs.Root>
      </div>
    </div>
  )
}
