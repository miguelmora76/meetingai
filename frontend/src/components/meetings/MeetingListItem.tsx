import { cn, formatDate, formatDuration } from '../../lib/utils'
import type { MeetingListItem as MeetingListItemType } from '../../types/api'
import { StatusBadge } from './StatusBadge'

interface MeetingListItemProps {
  meeting: MeetingListItemType
  isSelected: boolean
  onClick: () => void
}

export function MeetingListItem({ meeting, isSelected, onClick }: MeetingListItemProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left px-3 py-3 rounded-lg transition-colors text-sm',
        'hover:bg-[#2a2a3d]',
        isSelected ? 'bg-[#2a2a3d] border border-[#89b4fa]/30' : 'border border-transparent',
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <span
          className={cn(
            'font-medium leading-tight truncate flex-1',
            isSelected ? 'text-[#89b4fa]' : 'text-gray-100',
          )}
        >
          {meeting.title}
        </span>
        <StatusBadge status={meeting.status} />
      </div>
      <div className="flex items-center gap-2 text-[#6c7086] text-xs">
        <span>{formatDate(meeting.date ?? meeting.created_at)}</span>
        {meeting.duration_seconds != null && (
          <>
            <span>·</span>
            <span>{formatDuration(meeting.duration_seconds)}</span>
          </>
        )}
      </div>
    </button>
  )
}
