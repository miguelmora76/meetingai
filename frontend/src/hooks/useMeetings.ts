import { useQuery } from '@tanstack/react-query'
import { listMeetings } from '../api/meetings'

export function useMeetings() {
  return useQuery({
    queryKey: ['meetings'],
    queryFn: () => listMeetings(),
    staleTime: 15_000,
  })
}
