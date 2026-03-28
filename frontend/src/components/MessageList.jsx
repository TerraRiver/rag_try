import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'

export default function MessageList({
  messages,
  isLoading,
  isRestoring = false,
  onSend,
  starterPrompts = [],
}) {
  const bottomRef = useRef(null)

  useEffect(() => {
    const lastMessage = messages[messages.length - 1]
    if (!lastMessage) return

    if (lastMessage.role === 'user' || lastMessage.isStreaming) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  return (
    <div className="chat-scrollbar flex-1 min-h-0 overflow-y-auto px-4 py-4 md:px-8 md:py-6">
      {messages.length === 0 && !isLoading && !isRestoring && (
        <div className="mx-auto flex h-full w-full max-w-4xl items-center">
          <div className="w-full rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-[0_12px_36px_rgba(15,23,42,0.05)] md:rounded-[28px] md:p-8">
            <p className="section-label">开始提问</p>
            <h3 className="mt-4 max-w-2xl text-2xl font-semibold leading-tight text-[color:var(--ink)] md:text-[2.5rem]">
              从档案里提问题，
              <br />
              让答案带着出处回来。
            </h3>

            <div className="mt-6 grid gap-3 md:mt-8 md:grid-cols-3">
              {starterPrompts.map((prompt, index) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => onSend(prompt)}
                  className="group rounded-[18px] border border-[color:var(--line)] bg-white p-4 text-left transition hover:-translate-y-0.5 hover:border-[color:var(--accent)] hover:shadow-[0_10px_24px_rgba(15,23,42,0.06)] md:rounded-[20px]"
                >
                  <span className="text-[11px] uppercase tracking-[0.24em] text-[color:var(--accent)]">
                    Prompt 0{index + 1}
                  </span>
                  <p className="mt-3 text-sm leading-7 text-[color:var(--ink)]">{prompt}</p>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        {messages.map((message, idx) => (
          <MessageBubble key={message.id || idx} message={message} />
        ))}
      </div>
      <div ref={bottomRef} />
    </div>
  )
}
