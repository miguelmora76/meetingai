import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createIncident, uploadIncident, type CreateIncidentPayload } from '../api/incidents'

export function useCreateIncident(onSuccess?: (id: string) => void) {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateIncidentPayload) => createIncident(payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['incidents'] })
      onSuccess?.(data.id)
    },
  })
}

export function useUploadIncident(onSuccess?: (id: string) => void) {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: (formData: FormData) => uploadIncident(formData),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['incidents'] })
      onSuccess?.(data.id)
    },
  })
}
