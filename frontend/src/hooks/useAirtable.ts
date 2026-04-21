import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  connectAirtable,
  disconnectAirtable,
  getAirtableConnection,
  getAirtableImport,
  listAirtableBases,
  listAirtableTables,
  startAirtableImport,
} from '../api/airtable'
import type { AirtableImportRequest } from '../types/api'

export function useAirtableConnection() {
  return useQuery({
    queryKey: ['airtable', 'connection'],
    queryFn: getAirtableConnection,
    staleTime: 30_000,
  })
}

export function useConnectAirtable(onSuccess?: () => void) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (token: string) => connectAirtable(token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['airtable'] })
      onSuccess?.()
    },
  })
}

export function useDisconnectAirtable(onSuccess?: () => void) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => disconnectAirtable(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['airtable'] })
      onSuccess?.()
    },
  })
}

export function useAirtableBases(enabled = true) {
  return useQuery({
    queryKey: ['airtable', 'bases'],
    queryFn: listAirtableBases,
    enabled,
  })
}

export function useAirtableTables(baseId: string | null) {
  return useQuery({
    queryKey: ['airtable', 'bases', baseId, 'tables'],
    queryFn: () => listAirtableTables(baseId!),
    enabled: !!baseId,
  })
}

export function useStartAirtableImport(onSuccess?: (importId: string) => void) {
  return useMutation({
    mutationFn: (req: AirtableImportRequest) => startAirtableImport(req),
    onSuccess: (data) => {
      onSuccess?.(data.id)
    },
  })
}

export function useAirtableImportStatus(importId: string | null) {
  return useQuery({
    queryKey: ['airtable', 'imports', importId],
    queryFn: () => getAirtableImport(importId!),
    enabled: !!importId,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'completed' || status === 'failed') return false
      return 1500
    },
  })
}
