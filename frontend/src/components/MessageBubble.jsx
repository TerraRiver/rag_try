import ReactMarkdown from 'react-markdown'

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const isStreaming = !isUser && message.isStreaming

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div
        className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border text-xs font-semibold ${
          isUser
            ? 'border-[color:var(--accent)] bg-[color:var(--accent)] text-white'
            : 'border-[color:var(--line)] bg-[color:var(--surface-soft)] text-[color:var(--ink)]'
        }`}
      >
        {isUser ? '问' : '档'}
      </div>

      <div className={`flex max-w-[85%] flex-col gap-2 md:max-w-[78%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`overflow-hidden rounded-[22px] px-4 py-4 text-sm leading-7 shadow-[0_10px_28px_rgba(15,23,42,0.05)] md:px-5 ${
            isUser
              ? 'rounded-tr-md border border-[color:var(--accent)] bg-[color:var(--accent)] text-white'
              : 'rounded-tl-md border border-[color:var(--line)] bg-white text-[color:var(--ink)]'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="rich-markdown prose prose-sm max-w-none text-[color:var(--ink)] prose-p:my-2 prose-headings:text-[color:var(--ink)] prose-strong:text-[color:var(--ink)] prose-li:text-[color:var(--ink)] prose-pre:my-3 prose-pre:rounded-2xl prose-pre:bg-[color:var(--surface-dark)] prose-pre:text-stone-100 prose-code:rounded prose-code:bg-[color:var(--surface-soft)] prose-code:px-1 prose-code:text-[color:var(--accent)]">
              <ReactMarkdown>{message.content}</ReactMarkdown>
              {isStreaming && <span className="ml-1 inline-block h-4 w-1.5 animate-pulse rounded-full bg-[color:var(--accent)] align-[-2px]" />}
            </div>
          )}
        </div>

        {!isUser && message.sources && message.sources.length > 0 && (
          <details open className="w-full text-xs text-[color:var(--muted)]">
            <summary className="source-summary flex cursor-pointer list-none items-center gap-2 py-1 text-[11px] uppercase tracking-[0.24em] text-[color:var(--accent)]">
              参考来源
              <span className="rounded-full border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-2 py-0.5 text-[10px] tracking-[0.18em] text-[color:var(--muted)]">
                {message.sources.length} 条
              </span>
            </summary>
            <div className="mt-3 space-y-2.5">
              {message.sources.map((src, i) => {
                const lines = src.split('\n')
                return (
                  <div
                    key={i}
                    className="rounded-[18px] border border-[color:var(--line)] bg-[color:var(--surface)] px-4 py-3 text-[color:var(--muted)]"
                  >
                    {lines.map((line, j) => {
                      const urlMatch = line.match(/🔗\s*(https?:\/\/\S+)/)
                      if (urlMatch) {
                        return (
                          <div key={j}>
                            <a
                              href={urlMatch[1]}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="break-all text-[color:var(--accent)] transition hover:underline"
                            >
                              🔗 原文链接
                            </a>
                          </div>
                        )
                      }
                      return (
                        <div
                          key={j}
                          className={j === 0 ? 'font-medium text-[color:var(--ink)]' : 'mt-1 leading-6'}
                        >
                          {line}
                        </div>
                      )
                    })}
                  </div>
                )
              })}
            </div>
          </details>
        )}
      </div>
    </div>
  )
}
