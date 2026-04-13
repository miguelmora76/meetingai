import { useQuery } from '@tanstack/react-query'
import { getIncident } from '../api/incidents'

const POLLING_STATUSES = ['pending', 'analyzing', 'embedding']

export function useIncident(id: string | null) {
  return useQuery({
    queryKey: ['incident', id],
    queryFn: () => getIncident(id!),
    enabled: !!id,
    refetchInterval: (query) =>
      query.state.data && POLLING_STATUSES.includes(query.state.data.processing_status)
        ? 3000
        : false,
  })
}
