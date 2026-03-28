import { useEffect, useState } from 'react'
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
  const statusText = isLoading ? '生成中' : isRestoring ? '恢复中' : '就绪'
  const [viewportHeight, setViewportHeight] = useState(null)
  const [keyboardOffset, setKeyboardOffset] = useState(0)
  const isKeyboardOpen = keyboardOffset > 120

  useEffect(() => {
    if (typeof window === 'undefined') return undefined

    const viewport = window.visualViewport

    const syncViewport = () => {
      const nextHeight = viewport?.height || window.innerHeight
      const nextOffset = viewport
        ? Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop)
        : 0

      setViewportHeight(Math.round(nextHeight))
      setKeyboardOffset(Math.round(nextOffset))
    }

    syncViewport()

    viewport?.addEventListener('resize', syncViewport)
    viewport?.addEventListener('scroll', syncViewport)
    window.addEventListener('resize', syncViewport)

    return () => {
      viewport?.removeEventListener('resize', syncViewport)
      viewport?.removeEventListener('scroll', syncViewport)
      window.removeEventListener('resize', syncViewport)
    }
  }, [])

  return (
    <div
      className="h-[100dvh] overflow-hidden px-3 py-3 md:px-6 md:py-6"
      style={{
        height: viewportHeight ? `${viewportHeight}px` : '100dvh',
        paddingBottom: 'calc(env(safe-area-inset-bottom) + 0.75rem)',
      }}
    >
      <section className="mx-auto grid h-full max-w-7xl min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-3 lg:grid-cols-[320px_minmax(0,1fr)] lg:grid-rows-1 lg:gap-4">
        <div
          className={`overflow-hidden transition-all duration-200 lg:hidden ${
            isKeyboardOpen ? 'max-h-0 translate-y-[-8px] opacity-0' : 'max-h-20 translate-y-0 opacity-100'
          }`}
        >
          <div className="flex items-center justify-between gap-3 rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface)] px-4 py-3 shadow-[0_8px_24px_rgba(15,23,42,0.05)]">
            <p className="truncate text-sm font-medium text-[color:var(--ink)]">
              领导人讲话知识库问答 · 本地语料 RAG 检索、生成与来源回溯
            </p>
            <span className="shrink-0 rounded-full border border-[color:var(--line)] bg-white px-3 py-1 text-[11px] text-[color:var(--muted)]">
              {statusText}
            </span>
          </div>
        </div>

        <aside className="hidden min-h-0 gap-4 lg:grid lg:grid-rows-[auto_minmax(0,1fr)]">
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
                {statusText}
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

        <section className="flex min-h-0 flex-col overflow-hidden rounded-[24px] border border-[color:var(--line)] bg-[color:var(--panel)] shadow-[0_24px_72px_rgba(15,23,42,0.08)] lg:rounded-[28px]">
          <header className="border-b border-[color:var(--line)] px-4 py-4 md:px-8 md:py-5">
            <div className="flex items-center justify-between gap-3 md:hidden">
              <h2 className="truncate text-base font-semibold tracking-tight text-[color:var(--ink)]">
                知识库对话
              </h2>

              <div className="flex shrink-0 gap-2">
                <button
                  type="button"
                  onClick={onNewSession}
                  disabled={isLoading || isRestoring}
                  className="rounded-[12px] border border-[color:var(--line)] bg-white px-3 py-1.5 text-xs text-[color:var(--ink)] transition hover:border-[color:var(--accent)] hover:text-[color:var(--accent)] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  新建
                </button>
                <button
                  type="button"
                  onClick={onClearSession}
                  disabled={isLoading || isRestoring}
                  className="rounded-[12px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3 py-1.5 text-xs text-[color:var(--muted)] transition hover:border-[color:var(--accent)] hover:text-[color:var(--accent)] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  清空
                </button>
              </div>
            </div>

            <div className="hidden flex-col gap-3 md:flex md:flex-row md:items-start md:justify-between">
              <div className="min-w-0">
                <p className="section-label">交流窗口</p>
                <h2 className="mt-1.5 text-lg font-semibold tracking-tight text-[color:var(--ink)] md:mt-2 md:text-[2rem]">
                  与知识库对话
                </h2>
                <p className="mt-1.5 truncate text-[11px] tracking-[0.04em] text-[color:var(--muted)] md:mt-2">
                  会话：{sessionId}
                </p>
              </div>

              <div className="flex shrink-0 flex-wrap gap-2">
                <button
                  type="button"
                  onClick={onNewSession}
                  disabled={isLoading || isRestoring}
                  className="rounded-[12px] border border-[color:var(--line)] bg-white px-3.5 py-2 text-sm text-[color:var(--ink)] transition hover:border-[color:var(--accent)] hover:text-[color:var(--accent)] disabled:cursor-not-allowed disabled:opacity-60 md:rounded-[14px] md:px-4"
                >
                  新会话
                </button>
                <button
                  type="button"
                  onClick={onClearSession}
                  disabled={isLoading || isRestoring}
                  className="rounded-[12px] border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3.5 py-2 text-sm text-[color:var(--muted)] transition hover:border-[color:var(--accent)] hover:text-[color:var(--accent)] disabled:cursor-not-allowed disabled:opacity-60 md:rounded-[14px] md:px-4"
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

        <div className="h-[68px] lg:hidden" aria-hidden="true" />
      </section>

      <div
        className="fixed bottom-0 left-3 right-3 z-20 lg:hidden"
        style={{
          bottom: `calc(env(safe-area-inset-bottom) + 0.75rem + ${keyboardOffset}px)`,
        }}
      >
        <ProgressPanel
          loadingMeta={loadingMeta}
          isLoading={isLoading}
          stageOrder={stageOrder}
          compact
        />
      </div>
    </div>
  )
}
