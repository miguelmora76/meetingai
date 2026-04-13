interface ProcessingBannerProps {
  meetingTitle: string
}

export function ProcessingBanner({ meetingTitle }: ProcessingBannerProps) {
  return (
    <div className="rounded-lg bg-amber-900/30 border border-amber-700/40 p-4 mb-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="w-2 h-2 rounded-full bg-amber-400 pulse-dot" />
        <p className="text-sm text-amber-200">
          Processing &ldquo;{meetingTitle}&rdquo; &mdash; transcribing, summarizing, and
          embedding&hellip;
        </p>
      </div>
      <div className="w-full h-1.5 bg-amber-900/50 rounded-full overflow-hidden">
        <div className="h-full bg-amber-400 rounded-full progress-animate" />
      </div>
    </div>
  )
}
