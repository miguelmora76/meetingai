import { useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X, ExternalLink } from 'lucide-react'
import { useConnectAirtable } from '../../hooks/useAirtable'

interface ConnectAirtableDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConnected?: () => void
}

const REQUIRED_SCOPES = [
  'data.records:read',
  'schema.bases:read',
  'user.email:read',
]

export function ConnectAirtableDialog({ open, onOpenChange, onConnected }: ConnectAirtableDialogProps) {
  const [token, setToken] = useState('')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const mutation = useConnectAirtable(() => {
    setToken('')
    setErrorMsg(null)
    onOpenChange(false)
    onConnected?.()
  })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErrorMsg(null)
    const trimmed = token.trim()
    if (!trimmed) return
    try {
      await mutation.mutateAsync(trimmed)
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to connect')
    }
  }

  const inputClass =
    'w-full bg-[#232334] border border-[#313244] rounded-lg px-3 py-2 text-xs text-gray-100 placeholder-[#6c7086] focus:outline-none focus:border-[#89b4fa]/50 font-mono'

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 z-40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-[#1e1e2e] border border-[#313244] rounded-xl shadow-2xl z-50 p-5">
          <div className="flex items-center justify-between mb-4">
            <Dialog.Title className="text-sm font-semibold text-gray-100">
              Connect Airtable
            </Dialog.Title>
            <Dialog.Close className="text-[#6c7086] hover:text-gray-300 transition-colors">
              <X size={16} />
            </Dialog.Close>
          </div>

          <p className="text-xs text-[#a6adc8] mb-3">
            Paste a personal access token from Airtable. It's validated and stored encrypted —
            you can revoke it anytime from Airtable.
          </p>

          <a
            href="https://airtable.com/create/tokens"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs text-[#89b4fa] hover:underline mb-4"
          >
            Create a token at airtable.com <ExternalLink size={11} />
          </a>

          <div className="text-[10px] text-[#6c7086] mb-3">
            Required scopes:
            <ul className="mt-1 space-y-0.5">
              {REQUIRED_SCOPES.map((s) => (
                <li key={s} className="font-mono text-[#cdd6f4]">• {s}</li>
              ))}
            </ul>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-[10px] font-medium text-[#6c7086] uppercase tracking-wider mb-1">
                Personal access token
              </label>
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="pat..."
                autoComplete="off"
                required
                className={inputClass}
              />
            </div>

            {errorMsg && (
              <p className="text-xs text-[#f38ba8]">{errorMsg}</p>
            )}

            <button
              type="submit"
              disabled={mutation.isPending || !token.trim()}
              className="w-full py-2 px-4 bg-[#f5a97f] text-[#1e1e2e] rounded-lg text-xs font-semibold hover:bg-[#f5a97f]/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {mutation.isPending ? 'Validating…' : 'Connect'}
            </button>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
