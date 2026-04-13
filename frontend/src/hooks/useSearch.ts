import { useMutation } from '@tanstack/react-query'
import { searchMeetings } from '../api/search'
import type { SearchRequest } from '../types/api'

export function useSearch() {
  return useMutation({
    mutationFn: (req: SearchRequest) => searchMeetings(req),
  })
}
