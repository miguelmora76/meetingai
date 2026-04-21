import { useMemo, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X, ChevronRight, ChevronLeft, Loader2, CheckCircle2, XCircle } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import {
  useAirtableBases,
  useAirtableTables,
  useAirtableImportStatus,
  useStartAirtableImport,
} from '../../hooks/useAirtable'
import type { AirtableField, AirtableTable } from '../../types/api'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Step = 'base' | 'table' | 'fields' | 'progress'

const TEXT_FIELD_TYPES = new Set([
  'singleLineText',
  'multilineText',
  'richText',
  'email',
  'url',
  'phoneNumber',
  'formula',
  'rollup',
  'aiText',
])

export function AirtableImportDialog({ open, onOpenChange }: Props) {
  const qc = useQueryClient()
  const [step, setStep] = useState<Step>('base')
  const [baseId, setBaseId] = useState<string | null>(null)
  const [baseName, setBaseName] = useState<string | null>(null)
  const [table, setTable] = useState<AirtableTable | null>(null)
  const [titleField, setTitleField] = useState<string | null>(null)
  const [contentFields, setContentFields] = useState<string[]>([])
  const [importId, setImportId] = useState<string | null>(null)

  const basesQuery = useAirtableBases(open && step === 'base')
  const tablesQuery = useAirtableTables(step === 'table' ? baseId : null)
  const startImport = useStartAirtableImport((id) => {
    setImportId(id)
    setStep('progress')
  })
  const importStatus = useAirtableImportStatus(importId)

  const primaryFieldName = useMemo(() => {
    if (!table) return null
    const primary = table.fields.find((f) => f.id === table.primary_field_id)
    return primary?.name ?? table.fields[0]?.name ?? null
  }, [table])

  function reset() {
    setStep('base')
    setBaseId(null)
    setBaseName(null)
    setTable(null)
    setTitleField(null)
    setContentFields([])
    setImportId(null)
  }

  function handleClose(next: boolean) {
    if (!next) {
      reset()
      // Refresh docs so newly imported items show up.
      qc.invalidateQueries({ queryKey: ['docs'] })
    }
    onOpenChange(next)
  }

  function handlePickBase(id: string, name: string) {
    setBaseId(id)
    setBaseName(name)
    setStep('table')
  }

  function handlePickTable(t: AirtableTable) {
    setTable(t)
    const primary = t.fields.find((f) => f.id === t.primary_field_id)
    setTitleField(primary?.name ?? t.fields[0]?.name ?? null)
    const defaultContent = t.fields
      .filter((f) => TEXT_FIELD_TYPES.has(f.type) && f.id !== t.primary_field_id)
      .map((f) => f.name)
    setContentFields(defaultContent)
    setStep('fields')
  }

  function toggleContentField(name: string) {
    setContentFields((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name],
    )
  }

  async function handleStartImport() {
    if (!baseId || !table) return
    await startImport.mutateAsync({
      base_id: baseId,
      base_name: baseName ?? undefined,
      table_id: table.id,
      table_name: table.name,
      title_field: titleField ?? undefined,
      content_fields: contentFields,
    })
  }

  return (
    <Dialog.Root open={open} onOpenChange={handleClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 z-40" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-[#1e1e2e] border border-[#313244] rounded-xl shadow-2xl z-50 p-5 max-h-[85vh] flex flex-col">
          <div className="flex items-center justify-between mb-4 shrink-0">
            <Dialog.Title className="text-sm font-semibold text-gray-100">
              Import from Airtable
            </Dialog.Title>
            <Dialog.Close className="text-[#6c7086] hover:text-gray-300 transition-colors">
              <X size={16} />
            </Dialog.Close>
          </div>

          <StepIndicator current={step} />

          <div className="flex-1 overflow-y-auto mt-4">
            {step === 'base' && (
              <BaseStep
                loading={basesQuery.isLoading}
                error={basesQuery.error}
                bases={basesQuery.data?.bases ?? []}
                onPick={handlePickBase}
              />
            )}

            {step === 'table' && (
              <TableStep
                loading={tablesQuery.isLoading}
                error={tablesQuery.error}
                tables={tablesQuery.data?.tables ?? []}
                onPick={handlePickTable}
              />
            )}

            {step === 'fields' && table && (
              <FieldsStep
                table={table}
                titleField={titleField}
                contentFields={contentFields}
                primaryFieldName={primaryFieldName}
                onTitleChange={setTitleField}
                onToggleContent={toggleContentField}
              />
            )}

            {step === 'progress' && (
              <ProgressStep
                status={importStatus.data?.status}
                recordsTotal={importStatus.data?.records_total ?? 0}
                recordsProcessed={importStatus.data?.records_processed ?? 0}
                documentsCreated={importStatus.data?.documents_created ?? 0}
                errorMessage={importStatus.data?.error_message ?? null}
              />
            )}
          </div>

          <div className="flex items-center justify-between mt-4 pt-4 border-t border-[#313244] shrink-0">
            {step !== 'base' && step !== 'progress' ? (
              <button
                onClick={() => setStep(step === 'fields' ? 'table' : 'base')}
                className="inline-flex items-center gap-1 text-xs text-[#6c7086] hover:text-gray-300"
              >
                <ChevronLeft size={12} /> Back
              </button>
            ) : (
              <div />
            )}

            {step === 'fields' && (
              <button
                onClick={handleStartImport}
                disabled={!titleField || startImport.isPending}
                className="px-4 py-2 bg-[#f5a97f] text-[#1e1e2e] rounded-lg text-xs font-semibold hover:bg-[#f5a97f]/90 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {startImport.isPending ? 'Starting…' : 'Start import'}
              </button>
            )}

            {step === 'progress' && (importStatus.data?.status === 'completed' || importStatus.data?.status === 'failed') && (
              <button
                onClick={() => handleClose(false)}
                className="px-4 py-2 bg-[#313244] text-gray-200 rounded-lg text-xs font-medium hover:bg-[#3b3b52]"
              >
                Close
              </button>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

function StepIndicator({ current }: { current: Step }) {
  const steps: { key: Step; label: string }[] = [
    { key: 'base', label: 'Base' },
    { key: 'table', label: 'Table' },
    { key: 'fields', label: 'Fields' },
    { key: 'progress', label: 'Import' },
  ]
  const currentIdx = steps.findIndex((s) => s.key === current)
  return (
    <div className="flex items-center gap-2 text-[10px] text-[#6c7086]">
      {steps.map((s, i) => {
        const active = i === currentIdx
        const done = i < currentIdx
        return (
          <span key={s.key} className="flex items-center gap-2">
            <span
              className={
                active
                  ? 'text-[#f5a97f] font-semibold'
                  : done
                    ? 'text-[#a6e3a1]'
                    : 'text-[#45475a]'
              }
            >
              {i + 1}. {s.label}
            </span>
            {i < steps.length - 1 && <ChevronRight size={10} className="text-[#45475a]" />}
          </span>
        )
      })}
    </div>
  )
}

function BaseStep({
  loading,
  error,
  bases,
  onPick,
}: {
  loading: boolean
  error: unknown
  bases: Array<{ id: string; name: string }>
  onPick: (id: string, name: string) => void
}) {
  if (loading) return <Centered><Loader2 size={18} className="animate-spin text-[#6c7086]" /></Centered>
  if (error) return <ErrorMsg error={error} />
  if (bases.length === 0) {
    return <p className="text-xs text-[#6c7086] text-center py-8">No bases accessible with this token.</p>
  }
  return (
    <ul className="space-y-1">
      {bases.map((b) => (
        <li key={b.id}>
          <button
            onClick={() => onPick(b.id, b.name)}
            className="w-full text-left px-3 py-2 rounded-lg bg-[#232334] hover:bg-[#2a2a3d] border border-[#313244] text-xs text-gray-100 transition-colors"
          >
            <div className="font-medium">{b.name}</div>
            <div className="text-[10px] text-[#6c7086] font-mono">{b.id}</div>
          </button>
        </li>
      ))}
    </ul>
  )
}

function TableStep({
  loading,
  error,
  tables,
  onPick,
}: {
  loading: boolean
  error: unknown
  tables: AirtableTable[]
  onPick: (t: AirtableTable) => void
}) {
  if (loading) return <Centered><Loader2 size={18} className="animate-spin text-[#6c7086]" /></Centered>
  if (error) return <ErrorMsg error={error} />
  if (tables.length === 0) {
    return <p className="text-xs text-[#6c7086] text-center py-8">No tables in this base.</p>
  }
  return (
    <ul className="space-y-1">
      {tables.map((t) => (
        <li key={t.id}>
          <button
            onClick={() => onPick(t)}
            className="w-full text-left px-3 py-2 rounded-lg bg-[#232334] hover:bg-[#2a2a3d] border border-[#313244] text-xs text-gray-100 transition-colors"
          >
            <div className="font-medium">{t.name}</div>
            <div className="text-[10px] text-[#6c7086]">{t.fields.length} fields</div>
          </button>
        </li>
      ))}
    </ul>
  )
}

function FieldsStep({
  table,
  titleField,
  contentFields,
  primaryFieldName,
  onTitleChange,
  onToggleContent,
}: {
  table: AirtableTable
  titleField: string | null
  contentFields: string[]
  primaryFieldName: string | null
  onTitleChange: (name: string) => void
  onToggleContent: (name: string) => void
}) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-[10px] font-medium text-[#6c7086] uppercase tracking-wider mb-1">
          Title field
        </label>
        <select
          value={titleField ?? ''}
          onChange={(e) => onTitleChange(e.target.value)}
          className="w-full bg-[#232334] border border-[#313244] rounded-lg px-3 py-2 text-xs text-gray-100 focus:outline-none focus:border-[#89b4fa]/50"
        >
          {table.fields.map((f) => (
            <option key={f.id} value={f.name}>
              {f.name}
              {f.name === primaryFieldName ? ' (primary)' : ''} — {f.type}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-[10px] font-medium text-[#6c7086] uppercase tracking-wider mb-2">
          Fields to include in document body
        </label>
        <div className="space-y-1 max-h-64 overflow-y-auto">
          {table.fields.map((f) => (
            <FieldCheckbox
              key={f.id}
              field={f}
              checked={contentFields.includes(f.name)}
              onToggle={() => onToggleContent(f.name)}
            />
          ))}
        </div>
        <p className="text-[10px] text-[#6c7086] mt-2">
          Each checked field becomes a markdown section in the imported document.
        </p>
      </div>
    </div>
  )
}

function FieldCheckbox({
  field,
  checked,
  onToggle,
}: {
  field: AirtableField
  checked: boolean
  onToggle: () => void
}) {
  return (
    <label className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-[#232334] cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={onToggle}
        className="accent-[#f5a97f]"
      />
      <span className="text-xs text-gray-100 flex-1">{field.name}</span>
      <span className="text-[10px] text-[#6c7086] font-mono">{field.type}</span>
    </label>
  )
}

function ProgressStep({
  status,
  recordsTotal,
  recordsProcessed,
  documentsCreated,
  errorMessage,
}: {
  status: string | undefined
  recordsTotal: number
  recordsProcessed: number
  documentsCreated: number
  errorMessage: string | null
}) {
  const pct = recordsTotal > 0 ? Math.round((recordsProcessed / recordsTotal) * 100) : 0
  const done = status === 'completed'
  const failed = status === 'failed'

  return (
    <div className="space-y-4 py-4">
      <div className="flex items-center gap-3">
        {failed ? (
          <XCircle size={22} className="text-[#f38ba8]" />
        ) : done ? (
          <CheckCircle2 size={22} className="text-[#a6e3a1]" />
        ) : (
          <Loader2 size={22} className="animate-spin text-[#f5a97f]" />
        )}
        <div className="text-xs text-gray-100">
          {failed && 'Import failed'}
          {done && 'Import complete'}
          {!done && !failed && (status ? `Status: ${status}` : 'Starting…')}
        </div>
      </div>

      {!failed && (
        <>
          <div className="w-full h-2 bg-[#232334] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#f5a97f] transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-[#6c7086]">
            <span>
              {recordsProcessed} / {recordsTotal} records
            </span>
            <span>{documentsCreated} new documents</span>
          </div>
        </>
      )}

      {failed && errorMessage && (
        <p className="text-xs text-[#f38ba8] bg-[#f38ba8]/10 border border-[#f38ba8]/30 rounded-lg p-3">
          {errorMessage}
        </p>
      )}
    </div>
  )
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="flex items-center justify-center py-8">{children}</div>
}

function ErrorMsg({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : 'Failed to load'
  return <p className="text-xs text-[#f38ba8] text-center py-8">{msg}</p>
}
