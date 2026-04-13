import * as Select from '@radix-ui/react-select'
import { ChevronDown, Check } from 'lucide-react'
import type { MeetingListItem } from '../../types/api'

interface MeetingScopeSelectorProps {
  value: string
  onChange: (v: string) => void
  completedMeetings: MeetingListItem[]
}

export function MeetingScopeSelector({
  value,
  onChange,
  completedMeetings,
}: MeetingScopeSelectorProps) {
  const selectedMeeting = completedMeetings.find((m) => m.id === value)

  return (
    <div className="flex items-center gap-2">
      <Select.Root value={value} onValueChange={onChange}>
        <Select.Trigger className="flex items-center gap-1.5 px-3 py-1.5 bg-[#232334] border border-[#313244] rounded-lg text-xs text-gray-200 hover:border-[#89b4fa]/40 transition-colors focus:outline-none min-w-[160px]">
          <Select.Value />
          <Select.Icon className="ml-auto">
            <ChevronDown size={13} className="text-[#6c7086]" />
          </Select.Icon>
        </Select.Trigger>

        <Select.Portal>
          <Select.Content
            className="bg-[#232334] border border-[#313244] rounded-lg shadow-xl overflow-hidden z-50"
            position="popper"
            sideOffset={4}
          >
            <Select.Viewport className="p-1 max-h-60 overflow-y-auto">
              <Select.Item
                value="all"
                className="flex items-center gap-2 px-3 py-2 text-xs text-gray-200 rounded cursor-pointer hover:bg-[#313244]/60 focus:bg-[#313244]/60 focus:outline-none data-[state=checked]:text-[#89b4fa]"
              >
                <Select.ItemText>All Meetings</Select.ItemText>
                <Select.ItemIndicator className="ml-auto">
                  <Check size={12} />
                </Select.ItemIndicator>
              </Select.Item>

              {completedMeetings.length > 0 && (
                <Select.Separator className="h-px bg-[#313244] my-1" />
              )}

              {completedMeetings.map((m) => (
                <Select.Item
                  key={m.id}
                  value={m.id}
                  className="flex items-center gap-2 px-3 py-2 text-xs text-gray-200 rounded cursor-pointer hover:bg-[#313244]/60 focus:bg-[#313244]/60 focus:outline-none data-[state=checked]:text-[#89b4fa]"
                >
                  <Select.ItemText>
                    <span className="truncate max-w-[200px] block">{m.title}</span>
                  </Select.ItemText>
                  <Select.ItemIndicator className="ml-auto shrink-0">
                    <Check size={12} />
                  </Select.ItemIndicator>
                </Select.Item>
              ))}
            </Select.Viewport>
          </Select.Content>
        </Select.Portal>
      </Select.Root>

      {selectedMeeting && (
        <span className="flex items-center gap-1 px-2 py-1 bg-[#89b4fa]/10 border border-[#89b4fa]/20 rounded-full text-[10px] text-[#89b4fa] max-w-[180px]">
          <span className="truncate">Asking about: {selectedMeeting.title}</span>
        </span>
      )}
    </div>
  )
}
