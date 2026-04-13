import { useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X, Upload } from 'lucide-react'
import { useUploadMeeting } from '../../hooks/useUploadMeeting'

interface UploadDialogProps {
  open: boolean
  onOpenChange: (v: boolean) => void
  onUploaded: (id: string) => void
}

export function UploadDialog({ open, onOpenChange, onUploaded }: UploadDialogProps) {
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [date, setDate] = useState('')
  const [participants, setParticipants] = useState('')

  const upload = useUploadMeeting()

  function reset() {
    setFile(null)
    setTitle('')
    setDate('')
    setParticipants('')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file || !title.trim()) return

    const formData = new FormData()
    formData.append('file', file)
    formData.append('title', title.trim())
    if (date) formData.append('date', date)
    if (participants.trim()) formData.append('participants', participants.trim())

    try {
      const id = await upload.mutateAsync(formData)
      reset()
      onOpenChange(false)
      onUploaded(id)
    } catch {
      // error displayed below
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md bg-[#232334] border border-[#313244] rounded-xl shadow-2xl p-6 focus:outline-none">
          <div className="flex items-center justify-between mb-5">
            <Dialog.Title className="text-base font-semibold text-gray-100">
              Upload Recording
            </Dialog.Title>
            <Dialog.Close className="text-[#6c7086] hover:text-gray-300 transition-colors">
              <X size={18} />
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {/* File input */}
            <div>
              <label className="block text-xs text-[#6c7086] mb-1.5">
                Audio / Video File <span className="text-red-400">*</span>
              </label>
              <label className="flex flex-col items-center justify-center gap-2 w-full h-24 border-2 border-dashed border-[#313244] rounded-lg cursor-pointer hover:border-[#89b4fa]/50 transition-colors bg-[#181825]">
                <Upload size={20} className="text-[#6c7086]" />
                <span className="text-xs text-[#6c7086]">
                  {file ? file.name : 'Click to select file'}
                </span>
                <input
                  type="file"
                  accept="audio/*,video/*,.mp3,.mp4,.wav,.m4a,.ogg,.webm,.flac,.aac"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (f) {
                      setFile(f)
                      if (!title) setTitle(f.name.replace(/\.[^.]+$/, ''))
                    }
                  }}
                />
              </label>
            </div>

            {/* Title */}
            <div>
              <label className="block text-xs text-[#6c7086] mb-1.5">
                Title <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                placeholder="Q2 Planning Meeting"
                className="w-full bg-[#181825] border border-[#313244] rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-[#6c7086] focus:outline-none focus:border-[#89b4fa]/60 transition-colors"
              />
            </div>

            {/* Date */}
            <div>
              <label className="block text-xs text-[#6c7086] mb-1.5">Date (optional)</label>
              <input
                type="datetime-local"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full bg-[#181825] border border-[#313244] rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-[#89b4fa]/60 transition-colors [color-scheme:dark]"
              />
            </div>

            {/* Participants */}
            <div>
              <label className="block text-xs text-[#6c7086] mb-1.5">Participants (optional)</label>
              <input
                type="text"
                value={participants}
                onChange={(e) => setParticipants(e.target.value)}
                placeholder="Alice, Bob, Carol"
                className="w-full bg-[#181825] border border-[#313244] rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-[#6c7086] focus:outline-none focus:border-[#89b4fa]/60 transition-colors"
              />
            </div>

            {upload.error && (
              <p className="text-xs text-red-400 bg-red-900/20 border border-red-800/40 rounded-lg px-3 py-2">
                {upload.error.message}
              </p>
            )}

            <div className="flex gap-3 pt-1">
              <Dialog.Close
                type="button"
                className="flex-1 px-4 py-2 text-sm text-[#6c7086] border border-[#313244] rounded-lg hover:bg-[#313244]/50 transition-colors"
              >
                Cancel
              </Dialog.Close>
              <button
                type="submit"
                disabled={!file || !title.trim() || upload.isPending}
                className="flex-1 px-4 py-2 text-sm font-medium bg-[#89b4fa] text-[#1e1e2e] rounded-lg hover:bg-[#89b4fa]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {upload.isPending ? 'Uploading…' : 'Upload & Process'}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
