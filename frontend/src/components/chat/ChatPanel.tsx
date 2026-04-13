import { useState, useEffect, useRef, useCallback } from 'react'
import { Send, Search, MessageSquare, Trash2 } from 'lucide-react'
import { useQA } from '../../hooks/useQA'
import { useSearch } from '../../hooks/useSearch'
import { ScopeSelector } from './ScopeSelector'
import { ChatMessage } from './ChatMessage'
import type { MeetingListItem, IncidentListItem, DocumentListItem, ChatMessage as ChatMessageType } from '../../types/api'

interface ChatPanelProps {
  initialScope?: string
  meetings: MeetingListItem[]
  incidents: IncidentListItem[]
  docs: DocumentListItem[]
}

function generateId() {
  return Math.random().toString(36).slice(2, 10)
}

export function ChatPanel({ initialScope, meetings, incidents, docs }: ChatPanelProps) {
  const [scope, setScope] = useState<string>(initialScope ?? 'all')
  const [input, setInput] = useState('')
  const [mode, setMode] = useState<'qa' | 'search'>('qa')

  const qa = useQA()
  const search = useSearch()

  const [searchMessages, setSearchMessages] = useState<ChatMessageType[]>([])

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const completedMeetings = meetings.filter((m) => m.status === 'completed')
  const completedIncidents = incidents.filter((i) => i.processing_status === 'completed')
  const indexedDocs = docs.filter((d) => d.processing_status === 'completed')

  const messages = mode === 'qa' ? qa.messages : searchMessages
  const isPending = mode === 'qa' ? qa.isPending : search.isPending

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-grow textarea
  function handleInputChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
  }

  const handleSend = useCallback(async () => {
    const q = input.trim()
    if (!q || isPending) return

    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    // Encode scope into source_type + source_id
    let source_type: string | undefined
    let source_id: string | undefined
    if (scope && scope !== 'all') {
      const [type, id] = scope.split(':')
      source_type = type
      source_id = id
    }

    if (mode === 'qa') {
      await qa.ask(q, scope)
    } else {
      // Search mode
      const userMsg: ChatMessageType = {
        id: generateId(),
        role: 'user',
        content: q,
      }
      const pendingId = generateId()
      const pendingMsg: ChatMessageType = {
        id: pendingId,
        role: 'assistant',
        content: '',
        isPending: true,
      }
      setSearchMessages((prev) => [...prev, userMsg, pendingMsg])

      try {
        const result = await search.mutateAsync({ query: q, source_type, source_id })
        const content =
          result.results.length === 0
            ? 'No results found for your query.'
            : `Found ${result.results.length} result${result.results.length !== 1 ? 's' : ''} for "${result.query}"`

        setSearchMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId
              ? {
                  id: pendingId,
                  role: 'assistant' as const,
                  content,
                  sources: result.results,
                  isPending: false,
                }
              : m,
          ),
        )
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Search failed'
        setSearchMessages((prev) =>
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
    }
  }, [input, isPending, scope, mode, qa, search])

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleClear() {
    if (mode === 'qa') {
      qa.clearMessages()
    } else {
      setSearchMessages([])
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Top bar */}
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-[#313244] shrink-0">
        <ScopeSelector
          value={scope}
          onChange={setScope}
          completedMeetings={completedMeetings}
          completedIncidents={completedIncidents}
          indexedDocs={indexedDocs}
        />

        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={handleClear}
              className="p-1.5 text-[#6c7086] hover:text-gray-300 transition-colors"
              title="Clear conversation"
            >
              <Trash2 size={14} />
            </button>
          )}

          {/* Mode toggle */}
          <div className="flex bg-[#181825] border border-[#313244] rounded-lg p-0.5">
            <button
              onClick={() => setMode('qa')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                mode === 'qa'
                  ? 'bg-[#89b4fa]/10 text-[#89b4fa]'
                  : 'text-[#6c7086] hover:text-gray-300'
              }`}
            >
              <MessageSquare size={12} />
              Q&A
            </button>
            <button
              onClick={() => setMode('search')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                mode === 'search'
                  ? 'bg-[#89b4fa]/10 text-[#89b4fa]'
                  : 'text-[#6c7086] hover:text-gray-300'
              }`}
            >
              <Search size={12} />
              Search
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
            {mode === 'qa' ? (
              <>
                <MessageSquare size={32} className="text-[#313244]" />
                <p className="text-sm text-[#6c7086]">Ask a question about your meetings</p>
                <p className="text-xs text-[#6c7086]/70">
                  Use the scope selector to focus on a specific meeting
                </p>
              </>
            ) : (
              <>
                <Search size={32} className="text-[#313244]" />
                <p className="text-sm text-[#6c7086]">Search across your meeting transcripts</p>
                <p className="text-xs text-[#6c7086]/70">
                  Find relevant passages and quotes
                </p>
              </>
            )}
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 px-4 pb-4 pt-2 border-t border-[#313244]">
        <div className="flex items-end gap-2 bg-[#232334] border border-[#313244] rounded-xl p-2 focus-within:border-[#89b4fa]/40 transition-colors">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={mode === 'qa' ? 'Ask a question… (Enter to send, Shift+Enter for newline)' : 'Search for… (Enter to search)'}
            rows={1}
            className="flex-1 bg-transparent text-sm text-gray-100 placeholder-[#6c7086] resize-none focus:outline-none py-1 px-1 leading-relaxed min-h-[36px] max-h-[160px]"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isPending}
            className="shrink-0 p-2 bg-[#89b4fa] text-[#1e1e2e] rounded-lg hover:bg-[#89b4fa]/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}
