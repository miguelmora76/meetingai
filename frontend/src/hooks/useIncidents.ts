import { useQuery } from '@tanstack/react-query'
import { listIncidents } from '../api/incidents'

export function useIncidents() {
  return useQuery({
    queryKey: ['incidents'],
    queryFn: () => listIncidents(),
    refetchInterval: 5000,
  })
}
