import { useState } from 'react'
import { Upload, Search, Bot, AlertTriangle, FileText, ChevronDown, ChevronRight, Database } from 'lucide-react'
import { MeetingListItem } from '../meetings/MeetingListItem'
import { UploadDialog } from '../meetings/UploadDialog'
import { IncidentListItem } from '../incidents/IncidentListItem'
import { CreateIncidentDialog } from '../incidents/CreateIncidentDialog'
import { DocListItem } from '../docs/DocListItem'
import { UploadDocDialog } from '../docs/UploadDocDialog'
import { AirtableConnectionPill } from '../airtable/AirtableConnectionPill'
import { AirtableImportDialog } from '../airtable/AirtableImportDialog'
import { useAirtableConnection } from '../../hooks/useAirtable'
import type { MeetingListItem as MeetingType, IncidentListItem as IncidentType, DocumentListItem as DocType } from '../../types/api'

interface SidebarProps {
  selectedMeetingId: string | null
  selectedIncidentId: string | null
  meetings: MeetingType[]
  incidents: IncidentType[]
  docs: DocType[]
  onSelectMeeting: (id: string) => void
  onSelectIncident: (id: string) => void
  onOpenChat: () => void
  onUploadMeetingComplete: (id: string) => void
  onCreateIncidentComplete: (id: string) => void
}

function SectionHeader({
  label,
  count,
  expanded,
  onToggle,
  action,
}: {
  label: string
  count?: number
  expanded: boolean
  onToggle: () => void
  action?: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between px-3 py-1.5">
      <button
        onClick={onToggle}
        className="flex items-center gap-1 text-[10px] font-semibold text-[#6c7086] uppercase tracking-wider hover:text-gray-400 transition-colors"
      >
        {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        {label}
        {count != null && <span className="ml-1 normal-case font-normal">({count})</span>}
      </button>
      {action}
    </div>
  )
}

export function Sidebar({
  selectedMeetingId,
  selectedIncidentId,
  meetings,
  incidents,
  docs,
  onSelectMeeting,
  onSelectIncident,
  onOpenChat,
  onUploadMeetingComplete,
  onCreateIncidentComplete,
}: SidebarProps) {
  const [meetingUploadOpen, setMeetingUploadOpen] = useState(false)
  const [incidentDialogOpen, setIncidentDialogOpen] = useState(false)
  const [docUploadOpen, setDocUploadOpen] = useState(false)
  const [airtableImportOpen, setAirtableImportOpen] = useState(false)

  const [meetingsExpanded, setMeetingsExpanded] = useState(true)
  const [incidentsExpanded, setIncidentsExpanded] = useState(true)
  const [docsExpanded, setDocsExpanded] = useState(true)

  const { data: airtableConnection } = useAirtableConnection()
  const airtableConnected = airtableConnection?.connected ?? false

  return (
    <aside className="w-[280px] shrink-0 bg-[#1e1e2e] border-r border-[#313244] flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-5 pb-4 border-b border-[#313244] shrink-0">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <Bot size={18} className="text-[#89b4fa]" />
            <h1 className="text-sm font-bold text-gray-100">EngineerAI</h1>
          </div>
          <AirtableConnectionPill />
        </div>
        <p className="text-[10px] text-[#6c7086] ml-6">AI Engineering Assistant</p>
      </div>

      {/* Global Actions */}
      <div className="px-3 py-3 space-y-1.5 shrink-0 border-b border-[#313244]">
        <button
          onClick={onOpenChat}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-[#6c7086] border border-[#313244] rounded-lg hover:bg-[#2a2a3d] hover:text-gray-300 transition-colors"
        >
          <Search size={14} />
          Search / Ask All
        </button>
      </div>

      {/* Scrollable lists */}
      <div className="flex-1 overflow-y-auto py-2">

        {/* Meetings */}
        <SectionHeader
          label="Meetings"
          count={meetings.length}
          expanded={meetingsExpanded}
          onToggle={() => setMeetingsExpanded((v) => !v)}
          action={
            <button
              onClick={() => setMeetingUploadOpen(true)}
              className="p-1 text-[#6c7086] hover:text-[#89b4fa] transition-colors"
              title="Upload recording"
            >
              <Upload size={12} />
            </button>
          }
        />
        {meetingsExpanded && (
          <div className="px-2 pb-2 space-y-0.5">
            {meetings.length === 0 ? (
              <p className="text-[10px] text-[#45475a] px-2 py-1.5">No meetings yet</p>
            ) : (
              meetings.map((m) => (
                <MeetingListItem
                  key={m.id}
                  meeting={m}
                  isSelected={m.id === selectedMeetingId}
                  onClick={() => onSelectMeeting(m.id)}
                />
              ))
            )}
          </div>
        )}

        {/* Incidents */}
        <SectionHeader
          label="Incidents"
          count={incidents.length}
          expanded={incidentsExpanded}
          onToggle={() => setIncidentsExpanded((v) => !v)}
          action={
            <button
              onClick={() => setIncidentDialogOpen(true)}
              className="p-1 text-[#6c7086] hover:text-[#f38ba8] transition-colors"
              title="Log incident"
            >
              <AlertTriangle size={12} />
            </button>
          }
        />
        {incidentsExpanded && (
          <div className="px-2 pb-2 space-y-0.5">
            {incidents.length === 0 ? (
              <p className="text-[10px] text-[#45475a] px-2 py-1.5">No incidents logged</p>
            ) : (
              incidents.map((i) => (
                <IncidentListItem
                  key={i.id}
                  incident={i}
                  isSelected={i.id === selectedIncidentId}
                  onClick={() => onSelectIncident(i.id)}
                />
              ))
            )}
          </div>
        )}

        {/* Knowledge Base */}
        <SectionHeader
          label="Knowledge Base"
          count={docs.length}
          expanded={docsExpanded}
          onToggle={() => setDocsExpanded((v) => !v)}
          action={
            <div className="flex items-center gap-1">
              {airtableConnected && (
                <button
                  onClick={() => setAirtableImportOpen(true)}
                  className="p-1 text-[#6c7086] hover:text-[#f5a97f] transition-colors"
                  title="Import from Airtable"
                >
                  <Database size={12} />
                </button>
              )}
              <button
                onClick={() => setDocUploadOpen(true)}
                className="p-1 text-[#6c7086] hover:text-[#89dceb] transition-colors"
                title="Add document"
              >
                <FileText size={12} />
              </button>
            </div>
          }
        />
        {docsExpanded && (
          <div className="px-2 pb-2 space-y-0.5">
            {docs.length === 0 ? (
              <p className="text-[10px] text-[#45475a] px-2 py-1.5">No documents added</p>
            ) : (
              docs.map((d) => (
                <DocListItem
                  key={d.id}
                  doc={d}
                  isSelected={false}
                  onClick={() => {}}
                />
              ))
            )}
          </div>
        )}
      </div>

      {/* Dialogs */}
      <UploadDialog
        open={meetingUploadOpen}
        onOpenChange={setMeetingUploadOpen}
        onUploaded={(id) => {
          setMeetingUploadOpen(false)
          onUploadMeetingComplete(id)
        }}
      />
      <CreateIncidentDialog
        open={incidentDialogOpen}
        onOpenChange={setIncidentDialogOpen}
        onCreated={(id) => {
          setIncidentDialogOpen(false)
          onCreateIncidentComplete(id)
        }}
      />
      <UploadDocDialog
        open={docUploadOpen}
        onOpenChange={setDocUploadOpen}
        onUploaded={() => setDocUploadOpen(false)}
      />
      <AirtableImportDialog
        open={airtableImportOpen}
        onOpenChange={setAirtableImportOpen}
      />
    </aside>
  )
}
