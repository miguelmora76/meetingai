import { Quote } from 'lucide-react'
import { formatDate } from '../../lib/utils'
import type { ActionItem } from '../../types/api'

interface ActionItemsTabProps {
  items: ActionItem[]
}

function PriorityBadge({ priority }: { priority: string }) {
  if (priority === 'high') {
    return (
      <span className="px-2 py-0.5 rounded text-xs bg-red-900/60 text-red-300 capitalize">
        High
      </span>
    )
  }
  if (priority === 'medium') {
    return (
      <span className="px-2 py-0.5 rounded text-xs bg-yellow-900/60 text-yellow-300 capitalize">
        Medium
      </span>
    )
  }
  if (priority === 'low') {
    return (
      <span className="px-2 py-0.5 rounded text-xs bg-green-900/60 text-green-300 capitalize">
        Low
      </span>
    )
  }
  return (
    <span className="px-2 py-0.5 rounded text-xs bg-gray-700 text-gray-300 capitalize">
      {priority}
    </span>
  )
}

export function ActionItemsTab({ items }: ActionItemsTabProps) {
  if (items.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-[#6c7086] text-sm">
        No action items found
      </div>
    )
  }

  return (
    <div className="overflow-x-auto -mx-1">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-[#313244]">
            <th className="text-left text-xs text-[#6c7086] font-medium px-2 py-2">Description</th>
            <th className="text-left text-xs text-[#6c7086] font-medium px-2 py-2">Assignee</th>
            <th className="text-left text-xs text-[#6c7086] font-medium px-2 py-2">Due Date</th>
            <th className="text-left text-xs text-[#6c7086] font-medium px-2 py-2">Priority</th>
            <th className="text-left text-xs text-[#6c7086] font-medium px-2 py-2">Status</th>
            <th className="w-8 px-2 py-2" />
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.id}
              className="border-b border-[#313244]/50 hover:bg-[#2a2a3d]/40 transition-colors"
            >
              <td className="px-2 py-3 text-gray-200 max-w-xs">
                <span className="line-clamp-2">{item.description}</span>
              </td>
              <td className="px-2 py-3 text-[#6c7086] whitespace-nowrap">
                {item.assignee ?? '—'}
              </td>
              <td className="px-2 py-3 text-[#6c7086] whitespace-nowrap">
                {formatDate(item.due_date)}
              </td>
              <td className="px-2 py-3">
                <PriorityBadge priority={item.priority} />
              </td>
              <td className="px-2 py-3 text-[#6c7086] capitalize whitespace-nowrap">
                {item.status}
              </td>
              <td className="px-2 py-3">
                {item.source_quote && (
                  <div className="relative group">
                    <button className="text-[#6c7086] hover:text-[#89b4fa] transition-colors">
                      <Quote size={14} />
                    </button>
                    <div className="absolute right-0 top-6 z-10 hidden group-hover:block w-64 bg-[#1e1e2e] border border-[#313244] rounded-lg p-3 shadow-xl">
                      <p className="text-xs text-[#6c7086] italic leading-relaxed">
                        &ldquo;{item.source_quote}&rdquo;
                      </p>
                    </div>
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
