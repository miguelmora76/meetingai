import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { askQuestion } from '../api/search'
import type { ChatMessage } from '../types/api'

function generateId() {
  return Math.random().toString(36).slice(2, 10)
}

export function useQA() {
  const [messages, setMessages] = useState<ChatMessage[]>([])

  const mutation = useMutation({
    mutationFn: askQuestion,
  })

  const ask = useCallback(
    async (question: string, scope?: string) => {
      // scope encoding: "meeting:uuid" | "incident:uuid" | "doc:uuid" | "all" | undefined
      let source_type: string | undefined
      let source_id: string | undefined

      if (scope && scope !== 'all') {
        const [type, id] = scope.split(':')
        source_type = type
        source_id = id
      }

      const userMsg: ChatMessage = {
        id: generateId(),
        role: 'user',
        content: question,
      }
      const pendingId = generateId()
      const pendingMsg: ChatMessage = {
        id: pendingId,
        role: 'assistant',
        content: '',
        isPending: true,
      }

      setMessages((prev) => [...prev, userMsg, pendingMsg])

      try {
        const result = await mutation.mutateAsync({
          question,
          source_type,
          source_id,
        })

        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? {
                  id: pendingId,
                  role: 'assistant' as const,
                  content: result.answer,
                  sources: result.sources,
                  isPending: false,
                }
              : m,
          ),
        )
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'An error occurred'
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? {
                  id: pendingId,
                  role: 'assistant' as const,
                  content: `Error: ${errorMsg}`,
                  isPending: false,
                }
              : m,
          ),
        )
      }
    },
    [mutation],
  )

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  return {
    messages,
    ask,
    isPending: mutation.isPending,
    clearMessages,
  }
}
