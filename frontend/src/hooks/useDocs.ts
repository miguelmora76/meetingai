import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listDocuments, uploadDocument } from '../api/docs'

export function useDocs() {
  return useQuery({
    queryKey: ['docs'],
    queryFn: () => listDocuments(),
    refetchInterval: 5000,
  })
}

export function useUploadDoc(onSuccess?: (id: string) => void) {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: (formData: FormData) => uploadDocument(formData),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['docs'] })
      onSuccess?.(data.id)
    },
  })
}
