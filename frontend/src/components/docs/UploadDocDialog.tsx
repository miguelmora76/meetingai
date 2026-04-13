import { useState, useRef } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X, Upload } from 'lucide-react'
import { useUploadDoc } from '../../hooks/useDocs'

interface UploadDocDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onUploaded: (id: string) => void
}

const DOC_TYPES = [
  { value: 'architecture', label: 'Architecture' },
  { value: 'runbook', label: 'Runbook' },
  { value: 'api', label: 'API Docs' },
  { value: 'postmortem', label: 'Postmortem' },
  { value: 'other', label: 'Other' },
]

export function UploadDocDialog({ open, onOpenChange, onUploaded }: UploadDocDialogProps) {
  const [title, setTitle] = useState('')
  const [docType, setDocType] = useState('architecture')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const mutation = useUploadDoc((id) => {
    onUploaded(id)
    onOpenChange(false)
    setTitle('')
    setDocType('architecture')
    setSelectedFile(null)
  })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim() || !selectedFile) return
    const fd = new FormData()
    fd.append('file', selectedFile)
    fd.append('title', title.trim())
    fd.append('doc_type', docType)
    mutation.mutate(fd)
  }

  const inputClass =
    'w-full bg-[#232334] border border-[#313244] rounded-lg px-3 py-2 text-xs text-gray-100 placeholder-[#6c7086] focus:outline-none focus:border-[#89b4fa]/50'

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 z-40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-[#1e1e2e] border border-[#313244] rounded-xl shadow-2xl z-50 p-5">
          <div className="flex items-center justify-between mb-4">
            <Dialog.Title className="text-sm font-semibold text-gray-100">
              Add Knowledge Base Document
            </Dialog.Title>
            <Dialog.Close className="text-[#6c7086] hover:text-gray-300 transition-colors">
              <X size={16} />
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-[10px] font-medium text-[#6c7086] uppercase tracking-wider mb-1">
                Title *
              </label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Payment Service Architecture"
                required
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-[10px] font-medium text-[#6c7086] uppercase tracking-wider mb-1">
                Document type
              </label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className={`${inputClass} cursor-pointer`}
              >
                {DOC_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-medium text-[#6c7086] uppercase tracking-wider mb-1">
                File *
              </label>
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
                    <p className="text-xs text-[#6c7086]">Click to attach document</p>
                    <p className="text-[10px] text-[#45475a] mt-1">.txt .md .yaml .json .py</p>
                  </>
                )}
              </div>
            </div>

            {mutation.error && (
              <p className="text-xs text-[#f38ba8]">
                {mutation.error instanceof Error ? mutation.error.message : 'Upload failed'}
              </p>
            )}

            <button
              type="submit"
              disabled={mutation.isPending || !title.trim() || !selectedFile}
              className="w-full py-2 px-4 bg-[#89dceb] text-[#1e1e2e] rounded-lg text-xs font-semibold hover:bg-[#89dceb]/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {mutation.isPending ? 'Uploading…' : 'Upload & Index'}
            </button>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
