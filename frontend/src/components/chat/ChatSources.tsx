import * as Collapsible from '@radix-ui/react-collapsible'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { formatTimestamp } from '../../lib/utils'
import type { SearchResultItem } from '../../types/api'

interface ChatSourcesProps {
  sources: SearchResultItem[]
}

export function ChatSources({ sources }: ChatSourcesProps) {
  const [open, setOpen] = useState(false)

  if (sources.length === 0) return null

  return (
    <Collapsible.Root open={open} onOpenChange={setOpen} className="mt-3">
      <Collapsible.Trigger className="flex items-center gap-1.5 text-xs text-[#6c7086] hover:text-gray-300 transition-colors">
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        {sources.length} source{sources.length !== 1 ? 's' : ''}
      </Collapsible.Trigger>

      <Collapsible.Content className="mt-2 space-y-2">
        {sources.map((src, i) => (
          <div
            key={i}
            className="bg-[#181825] border border-[#313244] rounded-lg p-3 text-xs space-y-2"
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-[9px] text-[#45475a] uppercase shrink-0">
                  {src.source_type ?? 'meeting'}
                </span>
                <span className="text-[#89b4fa] font-medium truncate">
                  {src.source_title ?? src.meeting_title ?? '—'}
                </span>
              </div>
              {src.timestamp_start != null && (
                <span className="text-[#6c7086] font-mono shrink-0">
                  {formatTimestamp(src.timestamp_start)}
                </span>
              )}
            </div>

            {/* Similarity bar */}
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1 bg-[#313244] rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded-full transition-all"
                  style={{ width: `${Math.round(src.similarity_score * 100)}%` }}
                />
              </div>
              <span className="text-[#6c7086] tabular-nums shrink-0">
                {Math.round(src.similarity_score * 100)}%
              </span>
            </div>

            <p className="text-[#6c7086] leading-relaxed">
              {src.chunk_text.length > 150
                ? src.chunk_text.slice(0, 150) + '…'
                : src.chunk_text}
            </p>
          </div>
        ))}
      </Collapsible.Content>
    </Collapsible.Root>
  )
}
