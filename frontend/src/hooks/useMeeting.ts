import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getMeeting } from '../api/meetings'

const POLLING_STATUSES = ['uploaded', 'transcribing', 'summarizing', 'embedding']

export function useMeeting(id: string | null) {
  const queryClient = useQueryClient()
  const prevStatus = useRef<string | undefined>(undefined)

  const query = useQuery({
    queryKey: ['meeting', id],
    queryFn: () => getMeeting(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && POLLING_STATUSES.includes(status) ? 3000 : false
    },
  })

  useEffect(() => {
    const status = query.data?.status
    if (prevStatus.current && POLLING_STATUSES.includes(prevStatus.current) && !POLLING_STATUSES.includes(status ?? '')) {
      queryClient.invalidateQueries({ queryKey: ['meetings'] })
    }
    prevStatus.current = status
  }, [query.data?.status, queryClient])

  return query
}
