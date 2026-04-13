import type { IncidentSeverity } from '../../types/api'

interface SeverityBadgeProps {
  severity: IncidentSeverity | string
  className?: string
}

const SEVERITY_STYLES: Record<string, string> = {
  sev1: 'bg-red-500/20 text-red-400 border border-red-500/30',
  sev2: 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
  sev3: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  sev4: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
}

const SEVERITY_LABELS: Record<string, string> = {
  sev1: 'SEV1',
  sev2: 'SEV2',
  sev3: 'SEV3',
  sev4: 'SEV4',
}

export function SeverityBadge({ severity, className = '' }: SeverityBadgeProps) {
  const style = SEVERITY_STYLES[severity] ?? 'bg-[#313244] text-[#6c7086]'
  const label = SEVERITY_LABELS[severity] ?? severity.toUpperCase()

  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold ${style} ${className}`}>
      {label}
    </span>
  )
}
