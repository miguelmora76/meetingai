import { useState, useRef } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import * as Tabs from '@radix-ui/react-tabs'
import { X, Upload, AlertTriangle } from 'lucide-react'
import { useCreateIncident, useUploadIncident } from '../../hooks/useCreateIncident'

interface CreateIncidentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: (id: string) => void
}

export function CreateIncidentDialog({ open, onOpenChange, onCreated }: CreateIncidentDialogProps) {
  const [tab, setTab] = useState<'describe' | 'upload'>('describe')

  // Describe tab state
  const [title, setTitle] = useState('')
  const [severity, setSeverity] = useState('sev3')
  const [status, setStatus] = useState('open')
  const [services, setServices] = useState('')
  const [description, setDescription] = useState('')
  const [occurredAt, setOccurredAt] = useState('')

  // Upload tab state
  const [uploadTitle, setUploadTitle] = useState('')
  const [uploadSeverity, setUploadSeverity] = useState('sev3')
  const [uploadStatus, setUploadStatus] = useState('open')
  const [uploadServices, setUploadServices] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const createMutation = useCreateIncident((id) => {
    onCreated(id)
    onOpenChange(false)
    resetForm()
  })

  const uploadMutation = useUploadIncident((id) => {
    onCreated(id)
    onOpenChange(false)
    resetForm()
  })

  function resetForm() {
    setTitle('')
    setSeverity('sev3')
    setStatus('open')
    setServices('')
    setDescription('')
    setOccurredAt('')
    setUploadTitle('')
    setUploadSeverity('sev3')
    setUploadStatus('open')
    setUploadServices('')
    setSelectedFile(null)
  }

  async function handleDescribeSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    createMutation.mutate({
      title: title.trim(),
      severity,
      status,
      services_affected: services.split(',').map((s) => s.trim()).filter(Boolean),
      description: description.trim() || undefined,
      occurred_at: occurredAt || undefined,
    })
  }

  async function handleUploadSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!uploadTitle.trim() || !selectedFile) return
    const fd = new FormData()
    fd.append('file', selectedFile)
    fd.append('title', uploadTitle.trim())
    fd.append('severity', uploadSeverity)
    fd.append('status', uploadStatus)
    if (uploadServices) fd.append('services_affected', uploadServices)
    uploadMutation.mutate(fd)
  }

  const isPending = createMutation.isPending || uploadMutation.isPending
  const error = createMutation.error || uploadMutation.error

  const inputClass =
    'w-full bg-[#232334] border border-[#313244] rounded-lg px-3 py-2 text-xs text-gray-100 placeholder-[#6c7086] focus:outline-none focus:border-[#89b4fa]/50'
  const selectClass = `${inputClass} cursor-pointer`
  const labelClass = 'block text-[10px] font-medium text-[#6c7086] uppercase tracking-wider mb-1'

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 z-40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-[#1e1e2e] border border-[#313244] rounded-xl shadow-2xl z-50 p-5">
          <div className="flex items-center justify-between mb-4">
            <Dialog.Title className="flex items-center gap-2 text-sm font-semibold text-gray-100">
              <AlertTriangle size={16} className="text-[#f38ba8]" />
              Log Incident
            </Dialog.Title>
            <Dialog.Close className="text-[#6c7086] hover:text-gray-300 transition-colors">
              <X size={16} />
            </Dialog.Close>
          </div>

          <Tabs.Root value={tab} onValueChange={(v) => setTab(v as 'describe' | 'upload')}>
            <Tabs.List className="flex bg-[#181825] border border-[#313244] rounded-lg p-0.5 mb-4">
              {(['describe', 'upload'] as const).map((t) => (
                <Tabs.Trigger
                  key={t}
                  value={t}
                  className={`flex-1 py-1.5 rounded text-xs font-medium transition-colors ${
                    tab === t
                      ? 'bg-[#89b4fa]/10 text-[#89b4fa]'
                      : 'text-[#6c7086] hover:text-gray-300'
                  }`}
                >
                  {t === 'describe' ? 'Describe' : 'Upload File'}
                </Tabs.Trigger>
              ))}
            </Tabs.List>

            <Tabs.Content value="describe">
              <form onSubmit={handleDescribeSubmit} className="space-y-3">
                <div>
                  <label className={labelClass}>Title *</label>
                  <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. API latency spike — payment service"
                    required
                    className={inputClass}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={labelClass}>Severity</label>
                    <select value={severity} onChange={(e) => setSeverity(e.target.value)} className={selectClass}>
                      <option value="sev1">SEV1 — Critical</option>
                      <option value="sev2">SEV2 — High</option>
                      <option value="sev3">SEV3 — Medium</option>
                      <option value="sev4">SEV4 — Low</option>
                    </select>
                  </div>
                  <div>
                    <label className={labelClass}>Status</label>
                    <select value={status} onChange={(e) => setStatus(e.target.value)} className={selectClass}>
                      <option value="open">Open</option>
                      <option value="mitigated">Mitigated</option>
                      <option value="resolved">Resolved</option>
                      <option value="closed">Closed</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className={labelClass}>Services affected</label>
                  <input
                    value={services}
                    onChange={(e) => setServices(e.target.value)}
                    placeholder="payments, auth, api-gateway (comma-separated)"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Occurred at</label>
                  <input
                    type="datetime-local"
                    value={occurredAt}
                    onChange={(e) => setOccurredAt(e.target.value)}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Description / logs *</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Paste incident description, error messages, logs, or timeline…"
                    rows={5}
                    required
                    className={`${inputClass} resize-none`}
                  />
                </div>

                {error && (
                  <p className="text-xs text-[#f38ba8]">
                    {error instanceof Error ? error.message : 'Failed to create incident'}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={isPending || !title.trim() || !description.trim()}
                  className="w-full py-2 px-4 bg-[#f38ba8] text-[#1e1e2e] rounded-lg text-xs font-semibold hover:bg-[#f38ba8]/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  {isPending ? 'Submitting…' : 'Log & Analyze'}
                </button>
              </form>
            </Tabs.Content>

            <Tabs.Content value="upload">
              <form onSubmit={handleUploadSubmit} className="space-y-3">
                <div>
                  <label className={labelClass}>Title *</label>
                  <input
                    value={uploadTitle}
                    onChange={(e) => setUploadTitle(e.target.value)}
                    placeholder="e.g. DB outage 2026-03-15"
                    required
                    className={inputClass}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={labelClass}>Severity</label>
                    <select value={uploadSeverity} onChange={(e) => setUploadSeverity(e.target.value)} className={selectClass}>
                      <option value="sev1">SEV1 — Critical</option>
                      <option value="sev2">SEV2 — High</option>
                      <option value="sev3">SEV3 — Medium</option>
                      <option value="sev4">SEV4 — Low</option>
                    </select>
                  </div>
                  <div>
                    <label className={labelClass}>Status</label>
                    <select value={uploadStatus} onChange={(e) => setUploadStatus(e.target.value)} className={selectClass}>
                      <option value="open">Open</option>
                      <option value="mitigated">Mitigated</option>
                      <option value="resolved">Resolved</option>
                      <option value="closed">Closed</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className={labelClass}>Services affected</label>
                  <input
                    value={uploadServices}
                    onChange={(e) => setUploadServices(e.target.value)}
                    placeholder="payments, auth (comma-separated)"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Incident file *</label>
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="border border-dashed border-[#313244] rounded-lg p-4 text-center cursor-pointer hover:border-[#89b4fa]/50 transition-colors"
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      className="hidden"
                      accept=".txt,.md,.log,.yaml,.yml,.json,.csv,.py,.rst"
                      onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                    />
                    {selectedFile ? (
                      <p className="text-xs text-[#a6e3a1]">{selectedFile.name}</p>
                    ) : (
                      <>
                        <Upload size={20} className="mx-auto mb-2 text-[#6c7086]" />
                        <p className="text-xs text-[#6c7086]">
                          Click to attach log file or runbook
                        </p>
                        <p className="text-[10px] text-[#45475a] mt-1">.txt .md .log .json .yaml .py</p>
                      </>
                    )}
                  </div>
                </div>

                {error && (
                  <p className="text-xs text-[#f38ba8]">
                    {error instanceof Error ? error.message : 'Upload failed'}
                  </p>
                )}

                <button
                  type="submit"
                  disabled={isPending || !uploadTitle.trim() || !selectedFile}
                  className="w-full py-2 px-4 bg-[#f38ba8] text-[#1e1e2e] rounded-lg text-xs font-semibold hover:bg-[#f38ba8]/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  {isPending ? 'Uploading…' : 'Upload & Analyze'}
                </button>
              </form>
            </Tabs.Content>
          </Tabs.Root>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
