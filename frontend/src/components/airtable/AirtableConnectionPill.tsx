import { useState } from 'react'
import { Database, CheckCircle2, AlertTriangle } from 'lucide-react'
import { useAirtableConnection, useDisconnectAirtable } from '../../hooks/useAirtable'
import { ConnectAirtableDialog } from './ConnectAirtableDialog'

export function AirtableConnectionPill() {
  const { data, isLoading } = useAirtableConnection()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const disconnect = useDisconnectAirtable(() => setMenuOpen(false))

  if (isLoading) {
    return <div className="h-6 w-24 rounded-full bg-[#232334] animate-pulse" />
  }

  if (!data?.connected) {
    return (
      <>
        <button
          onClick={() => setDialogOpen(true)}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-medium text-[#f5a97f] border border-[#f5a97f]/30 rounded-full hover:bg-[#f5a97f]/10 transition-colors"
          title="Connect your Airtable account"
        >
          <Database size={11} />
          Connect Airtable
        </button>
        <ConnectAirtableDialog open={dialogOpen} onOpenChange={setDialogOpen} />
      </>
    )
  }

  const hasMissingScopes = (data.missing_required_scopes?.length ?? 0) > 0

  return (
    <div className="relative">
      <button
        onClick={() => setMenuOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-medium text-[#a6e3a1] border border-[#a6e3a1]/30 rounded-full hover:bg-[#a6e3a1]/10 transition-colors max-w-[180px]"
        title={data.airtable_email ?? 'Connected'}
      >
        {hasMissingScopes ? (
          <AlertTriangle size={11} className="text-[#f9e2af]" />
        ) : (
          <CheckCircle2 size={11} />
        )}
        <span className="truncate">{data.airtable_email ?? 'Airtable'}</span>
      </button>

      {menuOpen && (
        <div className="absolute right-0 mt-1 w-56 bg-[#232334] border border-[#313244] rounded-lg shadow-xl z-50 text-xs overflow-hidden">
          {hasMissingScopes && (
            <div className="px-3 py-2 text-[10px] text-[#f9e2af] border-b border-[#313244]">
              Missing scopes:
              <ul className="mt-1 space-y-0.5 font-mono text-[#cdd6f4]">
                {data.missing_required_scopes.map((s) => (
                  <li key={s}>• {s}</li>
                ))}
              </ul>
            </div>
          )}
          <button
            onClick={() => {
              setMenuOpen(false)
              setDialogOpen(true)
            }}
            className="w-full text-left px-3 py-2 hover:bg-[#313244] text-gray-200"
          >
            Reconnect with new token
          </button>
          <button
            onClick={() => disconnect.mutate()}
            disabled={disconnect.isPending}
            className="w-full text-left px-3 py-2 hover:bg-[#313244] text-[#f38ba8] disabled:opacity-40"
          >
            {disconnect.isPending ? 'Disconnecting…' : 'Disconnect'}
          </button>
        </div>
      )}

      <ConnectAirtableDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </div>
  )
}
