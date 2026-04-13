import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChatSources } from './ChatSources'
import type { ChatMessage as ChatMessageType } from '../../types/api'

interface ChatMessageProps {
  message: ChatMessageType
}

export function ChatMessage({ message }: ChatMessageProps) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[80%] px-4 py-2.5 bg-[#89b4fa] text-[#1e1e2e] rounded-2xl rounded-tr-sm text-sm leading-relaxed">
          {message.content}
        </div>
      </div>
    )
  }

  if (message.isPending) {
    return (
      <div className="flex justify-start mb-4">
        <div className="max-w-[80%] px-4 py-3 bg-[#232334] border border-[#313244] rounded-2xl rounded-tl-sm">
          <div className="flex items-center gap-1.5 h-5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#6c7086] typing-dot" />
            <span className="w-1.5 h-1.5 rounded-full bg-[#6c7086] typing-dot" />
            <span className="w-1.5 h-1.5 rounded-full bg-[#6c7086] typing-dot" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[85%] px-4 py-3 bg-[#232334] border border-[#313244] rounded-2xl rounded-tl-sm text-sm">
        <div className="text-gray-200 leading-relaxed">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              ul: ({ children }) => (
                <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>
              ),
              li: ({ children }) => <li className="text-gray-300">{children}</li>,
              strong: ({ children }) => (
                <strong className="font-semibold text-gray-100">{children}</strong>
              ),
              code: ({ children }) => (
                <code className="bg-[#313244] text-[#89b4fa] px-1.5 py-0.5 rounded text-xs font-mono">
                  {children}
                </code>
              ),
              h1: ({ children }) => (
                <h1 className="text-base font-bold text-gray-100 mt-3 mb-1 first:mt-0">
                  {children}
                </h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-sm font-semibold text-gray-100 mt-2 mb-1 first:mt-0">
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-sm font-semibold text-gray-200 mt-2 mb-1 first:mt-0">
                  {children}
                </h3>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
        {message.sources && message.sources.length > 0 && (
          <ChatSources sources={message.sources} />
        )}
      </div>
    </div>
  )
}
