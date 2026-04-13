import { Bot } from 'lucide-react'
import { MeetingDetail } from '../meetings/MeetingDetail'
import { IncidentDetail } from '../incidents/IncidentDetail'
import { ChatPanel } from '../chat/ChatPanel'
import type { MeetingListItem, IncidentListItem, DocumentListItem } from '../../types/api'

interface MainPanelProps {
  activeView: 'meeting' | 'incident' | 'chat' | 'empty'
  selectedMeetingId: string | null
  selectedIncidentId: string | null
  chatInitialScope?: string
  onOpenChat: (scope?: string) => void
  meetings: MeetingListItem[]
  incidents: IncidentListItem[]
  docs: DocumentListItem[]
}

export function MainPanel({
  activeView,
  selectedMeetingId,
  selectedIncidentId,
  chatInitialScope,
  onOpenChat,
  meetings,
  incidents,
  docs,
}: MainPanelProps) {
  if (activeView === 'meeting' && selectedMeetingId) {
    return (
      <main className="flex-1 bg-[#181825] overflow-hidden">
        <MeetingDetail
          meetingId={selectedMeetingId}
          onOpenChat={(meetingId) => onOpenChat(meetingId ? `meeting:${meetingId}` : undefined)}
        />
      </main>
    )
  }

  if (activeView === 'incident' && selectedIncidentId) {
    return (
      <main className="flex-1 bg-[#181825] overflow-hidden">
        <IncidentDetail
          incidentId={selectedIncidentId}
          onOpenChat={onOpenChat}
        />
      </main>
    )
  }

  if (activeView === 'chat') {
    return (
      <main className="flex-1 bg-[#181825] overflow-hidden">
        <ChatPanel
          initialScope={chatInitialScope}
          meetings={meetings}
          incidents={incidents}
          docs={docs}
        />
      </main>
    )
  }

  return (
    <main className="flex-1 bg-[#181825] flex flex-col items-center justify-center gap-4 text-center p-8">
      <div className="w-16 h-16 rounded-2xl bg-[#232334] border border-[#313244] flex items-center justify-center">
        <Bot size={28} className="text-[#313244]" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-[#6c7086]">AI Engineering Assistant</p>
        <p className="text-xs text-[#6c7086]/70">
          Upload meetings, log incidents, and add architecture docs
        </p>
      </div>
    </main>
  )
}
