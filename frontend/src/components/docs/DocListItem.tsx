import { FileText, Loader2 } from 'lucide-react'
import type { DocumentListItem } from '../../types/api'

interface DocListItemProps {
  doc: DocumentListItem
  isSelected: boolean
  onClick: () => void
}

export function DocListItem({ doc, isSelected, onClick }: DocListItemProps) {
  const isProcessing = ['pending', 'embedding'].includes(doc.processing_status)

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
        isSelected
          ? 'bg-[#89b4fa]/10 border border-[#89b4fa]/30'
          : 'hover:bg-[#2a2a3d] border border-transparent'
      }`}
    >
      <div className="flex items-start gap-2">
        <FileText size={12} className="text-[#89dceb] shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="text-xs text-gray-200 leading-tight truncate">{doc.title}</p>
          <div className="flex items-center gap-1.5 mt-1">
            {isProcessing && <Loader2 size={10} className="text-[#f9e2af] animate-spin" />}
            <span className="text-[10px] text-[#6c7086] capitalize">{doc.doc_type}</span>
            {doc.processing_status === 'failed' && (
              <span className="text-[10px] text-[#f38ba8]">· failed</span>
            )}
          </div>
        </div>
      </div>
    </button>
  )
}
