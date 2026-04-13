import * as Select from '@radix-ui/react-select'
import { ChevronDown } from 'lucide-react'
import type { MeetingListItem, IncidentListItem, DocumentListItem } from '../../types/api'

interface ScopeSelectorProps {
  value: string
  onChange: (value: string) => void
  completedMeetings: MeetingListItem[]
  completedIncidents: IncidentListItem[]
  indexedDocs: DocumentListItem[]
}

export function ScopeSelector({
  value,
  onChange,
  completedMeetings,
  completedIncidents,
  indexedDocs,
}: ScopeSelectorProps) {
  function getLabel(): string {
    if (value === 'all') return 'All sources'
    const [type, id] = value.split(':')
    if (type === 'meeting') {
      return completedMeetings.find((m) => m.id === id)?.title ?? 'Meeting'
    }
    if (type === 'incident') {
      return completedIncidents.find((i) => i.id === id)?.title ?? 'Incident'
    }
    if (type === 'doc') {
      return indexedDocs.find((d) => d.id === id)?.title ?? 'Document'
    }
    return 'All sources'
  }

  return (
    <Select.Root value={value} onValueChange={onChange}>
      <Select.Trigger className="flex items-center gap-1.5 text-xs text-[#6c7086] hover:text-gray-300 transition-colors outline-none max-w-[200px]">
        <Select.Value>
          <span className="truncate">{getLabel()}</span>
        </Select.Value>
        <Select.Icon>
          <ChevronDown size={12} />
        </Select.Icon>
      </Select.Trigger>

      <Select.Portal>
        <Select.Content
          position="popper"
          sideOffset={4}
          className="z-50 bg-[#232334] border border-[#313244] rounded-lg shadow-xl overflow-hidden w-64 max-h-72 overflow-y-auto"
        >
          <Select.Viewport className="p-1">
            <Select.Item
              value="all"
              className="flex items-center px-3 py-2 text-xs text-gray-200 rounded cursor-pointer hover:bg-[#89b4fa]/10 outline-none data-[highlighted]:bg-[#89b4fa]/10"
            >
              <Select.ItemText>All sources</Select.ItemText>
            </Select.Item>

            {completedMeetings.length > 0 && (
              <Select.Group>
                <Select.Label className="px-3 py-1 text-[9px] font-semibold text-[#45475a] uppercase tracking-wider">
                  Meetings
                </Select.Label>
                {completedMeetings.map((m) => (
                  <Select.Item
                    key={m.id}
                    value={`meeting:${m.id}`}
                    className="flex items-center px-3 py-2 text-xs text-gray-200 rounded cursor-pointer hover:bg-[#89b4fa]/10 outline-none data-[highlighted]:bg-[#89b4fa]/10"
                  >
                    <Select.ItemText>
                      <span className="truncate">{m.title}</span>
                    </Select.ItemText>
                  </Select.Item>
                ))}
              </Select.Group>
            )}

            {completedIncidents.length > 0 && (
              <Select.Group>
                <Select.Label className="px-3 py-1 text-[9px] font-semibold text-[#45475a] uppercase tracking-wider">
                  Incidents
                </Select.Label>
                {completedIncidents.map((i) => (
                  <Select.Item
                    key={i.id}
                    value={`incident:${i.id}`}
                    className="flex items-center px-3 py-2 text-xs text-gray-200 rounded cursor-pointer hover:bg-[#89b4fa]/10 outline-none data-[highlighted]:bg-[#89b4fa]/10"
                  >
                    <Select.ItemText>
                      <span className="truncate">{i.title}</span>
                    </Select.ItemText>
                  </Select.Item>
                ))}
              </Select.Group>
            )}

            {indexedDocs.length > 0 && (
              <Select.Group>
                <Select.Label className="px-3 py-1 text-[9px] font-semibold text-[#45475a] uppercase tracking-wider">
                  Knowledge Base
                </Select.Label>
                {indexedDocs.map((d) => (
                  <Select.Item
                    key={d.id}
                    value={`doc:${d.id}`}
                    className="flex items-center px-3 py-2 text-xs text-gray-200 rounded cursor-pointer hover:bg-[#89b4fa]/10 outline-none data-[highlighted]:bg-[#89b4fa]/10"
                  >
                    <Select.ItemText>
                      <span className="truncate">{d.title}</span>
                    </Select.ItemText>
                  </Select.Item>
                ))}
              </Select.Group>
            )}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  )
}
