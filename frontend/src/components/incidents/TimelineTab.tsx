import { formatDate } from '../../lib/utils'
import type { IncidentTimelineEvent } from '../../types/api'

interface TimelineTabProps {
  events: IncidentTimelineEvent[]
}

const EVENT_TYPE_STYLES: Record<string, string> = {
  detection: 'bg-red-500/20 text-red-400 border-red-500/30',
  escalation: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  mitigation: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  resolution: 'bg-green-500/20 text-green-400 border-green-500/30',
  event: 'bg-[#313244] text-[#6c7086] border-[#45475a]',
}

const EVENT_TYPE_DOT: Record<string, string> = {
  detection: 'bg-red-400',
  escalation: 'bg-orange-400',
  mitigation: 'bg-yellow-400',
  resolution: 'bg-green-400',
  event: 'bg-[#6c7086]',
}

export function TimelineTab({ events }: TimelineTabProps) {
  if (events.length === 0) {
    return (
      <div className="p-4 text-center text-[#6c7086] text-xs">
        No timeline events extracted.
      </div>
    )
  }

  return (
    <div className="p-4">
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-3 top-1 bottom-1 w-px bg-[#313244]" />

        <div className="space-y-4">
          {events.map((ev) => {
            const dotColor = EVENT_TYPE_DOT[ev.event_type] ?? EVENT_TYPE_DOT.event
            const badgeStyle = EVENT_TYPE_STYLES[ev.event_type] ?? EVENT_TYPE_STYLES.event

            return (
              <div key={ev.id ?? ev.event_index} className="flex gap-4 pl-1">
                <div className={`w-5 h-5 rounded-full shrink-0 flex items-center justify-center border ${badgeStyle}`}>
                  <div className={`w-2 h-2 rounded-full ${dotColor}`} />
                </div>
                <div className="flex-1 min-w-0 pb-1">
                  {ev.occurred_at && (
                    <p className="text-[10px] text-[#6c7086] mb-1">{formatDate(ev.occurred_at)}</p>
                  )}
                  <p className="text-xs text-gray-200 leading-relaxed">{ev.description}</p>
                  <span className={`inline-flex items-center mt-1.5 px-1.5 py-0.5 rounded text-[9px] font-medium border ${badgeStyle}`}>
                    {ev.event_type}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
