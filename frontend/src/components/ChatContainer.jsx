import MessageList from './MessageList'
import ChatInput from './ChatInput'
import ProgressPanel from './ProgressPanel'

const STARTER_PROMPTS = [
  '总结习总书记关于青少年健康成长的重要论述。',
  '对比不同时期讲话中“改革”相关表述的变化。',
  '找出和“高质量发展”最相关的讲话并概括观点。',
]

export default function ChatContainer({
  messages,
  isLoading,
  isRestoring,
  loadingMeta,
  stageOrder,
  sessionId,
  onNewSession,
  onClearSession,
  onSend,
}) {
  return (
    <div className="h-[100dvh] overflow-hidden px-3 py-3 md:px-6 md:py-6">
      <section className="mx-auto grid h-full max-w-7xl gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="grid min-h-0 gap-4 lg:grid-rows-[auto_minmax(0,1fr)]">
          <div className="rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface)] p-4 shadow-[0_10px_28px_rgba(15,23,42,0.05)] md:p-5">
            <p className="section-label">平台简介</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[color:var(--ink)]">
              领导人讲话知识库问答
            </h1>
            <p className="mt-2.5 text-sm leading-7 text-[color:var(--muted)]">
              这是一个面向本地讲话语料的 RAG 平台，支持混合检索、流式生成、多轮追问和来源回溯。
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-full border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3 py-1.5 text-xs text-[color:var(--muted)]">
                本地知识库
              </span>
              <span className="rounded-full border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3 py-1.5 text-xs text-[color:var(--muted)]">
                {messages.length} 条消息
              </span>
              <span className="rounded-full border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3 py-1.5 text-xs text-[color:var(--muted)]">
                {isLoading ? '生成中' : isRestoring ? '恢复中' : '就绪'}
              </span>
            </div>
          </div>

          <div className="min-h-0">
            <ProgressPanel
              loadingMeta={loadingMeta}
              isLoading={isLoading}
              stageOrder={stageOrder}
            />
          </div>
        </aside>

        <section className="flex min-h-0 flex-col overflow-hidden rounded-[28px] border border-[color:var(--line)] bg-[color:var(--panel)] shadow-[0_24px_72px_rgba(15,23,42,0.08)]">
          <header className="border-b border-[color:var(--line)] px-5 py-5 md:px-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="section-label">交流窗口</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[color:var(--ink)] md:text-[2rem]">
                  与知识库对话
                </h2>
                <p className="mt-2 text-[11px] tracking-[0.04em] text-[color:var(--muted)]">
                  会话：{sessionId}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={onNewSession}
                  disabled={isLoading || isRestoring}
                  className="rounded-[14px] border border-[color:var(--line)] bg-white px-4 py-2 text-sm text-[color:var(--ink)] transition hover:border-[color:var(--accent)] hover:text-[color:var(--accent)] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  新会话
                </button>
                <button
                  type="button"
                  onClick={onClearSession}
                  disabled={isLoading || isRestoring}
                  className="rounded-[14px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-4 py-2 text-sm text-[color:var(--muted)] transition hover:border-[color:var(--accent)] hover:text-[color:var(--accent)] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  清空上下文
                </button>
              </div>
            </div>
          </header>

          <MessageList
            messages={messages}
            isLoading={isLoading}
            isRestoring={isRestoring}
            onSend={onSend}
            starterPrompts={STARTER_PROMPTS}
          />
          <ChatInput onSend={onSend} isLoading={isLoading} isRestoring={isRestoring} />
        </section>
      </section>
    </div>
  )
}
