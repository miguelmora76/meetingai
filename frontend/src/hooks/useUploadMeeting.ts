import { useMutation, useQueryClient } from '@tanstack/react-query'
import { uploadMeeting, processMeeting } from '../api/meetings'

export function useUploadMeeting() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (formData: FormData): Promise<string> => {
      const uploaded = await uploadMeeting(formData)
      await processMeeting(uploaded.id)
      return uploaded.id
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meetings'] })
    },
  })
}
