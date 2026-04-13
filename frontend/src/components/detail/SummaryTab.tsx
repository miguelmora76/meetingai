import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface SummaryTabProps {
  summary: string | null
  status: string
}

export function SummaryTab({ summary, status }: SummaryTabProps) {
  if (status === 'processing' || status === 'uploaded') {
    return (
      <div className="space-y-3 animate-pulse">
        <div className="h-4 bg-[#313244] rounded w-3/4" />
        <div className="h-4 bg-[#313244] rounded w-full" />
        <div className="h-4 bg-[#313244] rounded w-5/6" />
        <div className="h-4 bg-[#313244] rounded w-2/3" />
        <div className="h-4 bg-[#313244] rounded w-full" />
        <div className="h-4 bg-[#313244] rounded w-4/5" />
      </div>
    )
  }

  if (!summary) {
    return (
      <div className="flex items-center justify-center h-32 text-[#6c7086] text-sm">
        Not yet available
      </div>
    )
  }

  return (
    <div className="prose-custom text-sm text-gray-200 leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-lg font-bold text-gray-100 mt-5 mb-2 first:mt-0">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-base font-semibold text-gray-100 mt-4 mb-2 first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-semibold text-gray-200 mt-3 mb-1.5 first:mt-0">
              {children}
            </h3>
          ),
          p: ({ children }) => <p className="mb-3 last:mb-0 text-gray-300">{children}</p>,
          ul: ({ children }) => (
            <ul className="list-disc list-inside mb-3 space-y-1 text-gray-300">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside mb-3 space-y-1 text-gray-300">{children}</ol>
          ),
          li: ({ children }) => <li className="text-gray-300">{children}</li>,
          strong: ({ children }) => (
            <strong className="font-semibold text-gray-100">{children}</strong>
          ),
          em: ({ children }) => <em className="italic text-gray-300">{children}</em>,
          code: ({ children }) => (
            <code className="bg-[#313244] text-[#89b4fa] px-1.5 py-0.5 rounded text-xs font-mono">
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="bg-[#181825] border border-[#313244] rounded-lg p-3 overflow-x-auto text-xs font-mono mb-3">
              {children}
            </pre>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-[#89b4fa]/40 pl-3 my-3 text-[#6c7086] italic">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="border-[#313244] my-4" />,
        }}
      >
        {summary}
      </ReactMarkdown>
    </div>
  )
}
