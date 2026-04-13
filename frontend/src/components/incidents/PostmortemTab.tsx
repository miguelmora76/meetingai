import ReactMarkdown from 'react-markdown'
import type { IncidentPostmortem } from '../../types/api'

interface PostmortemTabProps {
  postmortem: IncidentPostmortem | null
}

export function PostmortemTab({ postmortem }: PostmortemTabProps) {
  if (!postmortem) {
    return (
      <div className="p-4 text-center text-[#6c7086] text-xs">
        No postmortem generated yet.
      </div>
    )
  }

  return (
    <div className="p-4 space-y-6">
      {postmortem.executive_summary && (
        <section>
          <h3 className="text-[10px] font-bold text-[#89b4fa] uppercase tracking-wider mb-3">
            Executive Summary
          </h3>
          <div className="prose prose-invert prose-sm max-w-none text-xs text-gray-300 leading-relaxed">
            <ReactMarkdown>{postmortem.executive_summary}</ReactMarkdown>
          </div>
        </section>
      )}

      {postmortem.root_cause_analysis && (
        <section>
          <h3 className="text-[10px] font-bold text-[#f9e2af] uppercase tracking-wider mb-3">
            Root Cause Analysis
          </h3>
          <div className="prose prose-invert prose-sm max-w-none text-xs text-gray-300 leading-relaxed">
            <ReactMarkdown>{postmortem.root_cause_analysis}</ReactMarkdown>
          </div>
        </section>
      )}

      {postmortem.model_used && (
        <p className="text-[10px] text-[#45475a]">Model: {postmortem.model_used}</p>
      )}
    </div>
  )
}
