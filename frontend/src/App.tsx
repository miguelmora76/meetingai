import { useState } from 'react'
import { Sidebar } from './components/layout/Sidebar'
import { MainPanel } from './components/layout/MainPanel'
import { useMeetings } from './hooks/useMeetings'
import { useIncidents } from './hooks/useIncidents'
import { useDocs } from './hooks/useDocs'

type ActiveView = 'meeting' | 'incident' | 'chat' | 'empty'

export default function App() {
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null)
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<ActiveView>('empty')
  const [chatInitialScope, setChatInitialScope] = useState<string | undefined>(undefined)

  const { data: meetingsData } = useMeetings()
  const { data: incidentsData } = useIncidents()
  const { data: docsData } = useDocs()

  const meetings = meetingsData?.items ?? []
  const incidents = incidentsData?.items ?? []
  const docs = docsData?.items ?? []

  function handleSelectMeeting(id: string) {
    setSelectedMeetingId(id)
    setActiveView('meeting')
  }

  function handleSelectIncident(id: string) {
    setSelectedIncidentId(id)
    setActiveView('incident')
  }

  function handleOpenChat(scope?: string) {
    setChatInitialScope(scope)
    setActiveView('chat')
  }

  function handleUploadMeetingComplete(id: string) {
    setSelectedMeetingId(id)
    setActiveView('meeting')
  }

  function handleCreateIncidentComplete(id: string) {
    setSelectedIncidentId(id)
    setActiveView('incident')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#181825] text-gray-100">
      <Sidebar
        selectedMeetingId={selectedMeetingId}
        selectedIncidentId={selectedIncidentId}
        meetings={meetings}
        incidents={incidents}
        docs={docs}
        onSelectMeeting={handleSelectMeeting}
        onSelectIncident={handleSelectIncident}
        onOpenChat={() => handleOpenChat()}
        onUploadMeetingComplete={handleUploadMeetingComplete}
        onCreateIncidentComplete={handleCreateIncidentComplete}
      />
      <MainPanel
        activeView={activeView}
        selectedMeetingId={selectedMeetingId}
        selectedIncidentId={selectedIncidentId}
        chatInitialScope={chatInitialScope}
        onOpenChat={handleOpenChat}
        meetings={meetings}
        incidents={incidents}
        docs={docs}
      />
    </div>
  )
}
