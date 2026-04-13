import type { IncidentActionItem } from '../../types/api'

interface IncidentActionItemsTabProps {
  actionItems: IncidentActionItem[]
}

const PRIORITY_STYLES: Record<string, string> = {
  high: 'text-[#f38ba8] bg-[#f38ba8]/10',
  medium: 'text-[#f9e2af] bg-[#f9e2af]/10',
  low: 'text-[#a6e3a1] bg-[#a6e3a1]/10',
}

const CATEGORY_STYLES: Record<string, string> = {
  prevention: 'bg-purple-500/10 text-purple-400',
  detection: 'bg-blue-500/10 text-blue-400',
  mitigation: 'bg-yellow-500/10 text-yellow-400',
  process: 'bg-green-500/10 text-green-400',
  documentation: 'bg-gray-500/10 text-gray-400',
}

export function IncidentActionItemsTab({ actionItems }: IncidentActionItemsTabProps) {
  if (actionItems.length === 0) {
    return (
      <div className="p-4 text-center text-[#6c7086] text-xs">
        No action items extracted.
      </div>
    )
  }

  return (
    <div className="p-4 space-y-2">
      {actionItems.map((item, i) => {
        const priorityStyle = PRIORITY_STYLES[item.priority] ?? PRIORITY_STYLES.medium
        const categoryStyle = item.category ? (CATEGORY_STYLES[item.category] ?? 'bg-[#313244] text-[#6c7086]') : null

        return (
          <div
            key={item.id ?? i}
            className="bg-[#232334] border border-[#313244] rounded-lg p-3 space-y-2"
          >
            <p className="text-xs text-gray-200 leading-relaxed">{item.description}</p>
            <div className="flex items-center flex-wrap gap-2">
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${priorityStyle}`}>
                {item.priority}
              </span>
              {categoryStyle && item.category && (
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${categoryStyle}`}>
                  {item.category}
                </span>
              )}
              {item.assignee && (
                <span className="text-[10px] text-[#6c7086]">→ {item.assignee}</span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
