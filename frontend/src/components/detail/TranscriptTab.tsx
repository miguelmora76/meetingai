import { formatTimestamp } from '../../lib/utils'
import type { Transcript } from '../../types/api'

interface TranscriptTabProps {
  transcript: Transcript | null
  status: string
}

const SPEAKER_COLORS = [
  'text-[#89b4fa]',
  'text-[#a6e3a1]',
  'text-[#fab387]',
  'text-[#f38ba8]',
  'text-[#cba6f7]',
  'text-[#94e2d5]',
]

function hashSpeaker(name: string): number {
  let h = 0
  for (let i = 0; i < name.length; i++) {
    h = (h * 31 + name.charCodeAt(i)) >>> 0
  }
  return h % SPEAKER_COLORS.length
}

export function TranscriptTab({ transcript, status }: TranscriptTabProps) {
  if (status === 'processing' || status === 'uploaded') {
    return (
      <div className="space-y-4 animate-pulse">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex gap-3">
            <div className="h-4 bg-[#313244] rounded w-10 shrink-0" />
            <div className="flex-1 space-y-1.5">
              <div className="h-3.5 bg-[#313244] rounded w-20" />
              <div className="h-4 bg-[#313244] rounded w-full" />
              <div className="h-4 bg-[#313244] rounded w-4/5" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (!transcript) {
    return (
      <div className="flex items-center justify-center h-32 text-[#6c7086] text-sm">
        No transcript available
      </div>
    )
  }

  if (transcript.segments && transcript.segments.length > 0) {
    return (
      <div className="space-y-4">
        {transcript.segments.map((seg, i) => (
          <div key={i} className="flex gap-3 text-sm">
            <span className="text-[#6c7086] font-mono text-xs pt-0.5 w-10 shrink-0">
              {formatTimestamp(seg.start_time)}
            </span>
            <div className="flex-1">
              {seg.speaker && (
                <span className={`font-semibold text-xs mb-1 block ${SPEAKER_COLORS[hashSpeaker(seg.speaker)]}`}>
                  {seg.speaker}
                </span>
              )}
              <p className="text-gray-300 leading-relaxed">{seg.text}</p>
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <pre className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed font-sans">
      {transcript.full_text}
    </pre>
  )
}
