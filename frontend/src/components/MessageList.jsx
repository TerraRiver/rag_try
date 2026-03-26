import { useEffect, useMemo, useRef, useState } from 'react'
import MessageBubble from './MessageBubble'

function formatElapsed(ms) {
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, '0')
  const seconds = String(totalSeconds % 60).padStart(2, '0')
  return `${minutes}:${seconds}`
}

function ThinkingStatus({ loadingMeta }) {
  const [now, setNow] = useState(Date.now())

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])

  const elapsedText = useMemo(() => {
    if (!loadingMeta?.startedAt) return '00:00'
    return formatElapsed(Math.max(0, now - loadingMeta.startedAt))
  }, [loadingMeta?.startedAt, now])

  const stageOrder = loadingMeta?.stageOrder || []
  const currentStage = loadingMeta?.currentStage
  const currentIndex = stageOrder.findIndex((stage) => stage.key === currentStage)
  const currentLabel =
    stageOrder.find((stage) => stage.key === currentStage)?.label ||
    loadingMeta?.stages?.find((stage) => stage.key === currentStage)?.label ||
    '处理中'

  return (
    <div className="flex items-start gap-2">
      <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-xs flex-shrink-0">
        AI
      </div>
      <div className="bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-gray-100 min-w-[260px] max-w-[360px]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-gray-500 text-sm">思考中</span>
            <span className="flex gap-1 items-center">
              {[0, 150, 300].map((delay) => (
                <span
                  key={delay}
                  className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce"
                  style={{ animationDelay: `${delay}ms` }}
                />
              ))}
            </span>
          </div>
          <span className="text-xs font-mono text-blue-500">{elapsedText}</span>
        </div>

        <p className="text-xs text-gray-500 mt-2">当前阶段：{currentLabel}</p>

        <div className="mt-2 space-y-1.5">
          {stageOrder.map((stage, index) => {
            const isCurrent = index === currentIndex
            const isDone = currentIndex > index
            const statusClass = isDone
              ? 'bg-emerald-500'
              : isCurrent
                ? 'bg-blue-500 animate-pulse'
                : 'bg-gray-200'
            const textClass = isCurrent ? 'text-gray-700' : isDone ? 'text-gray-600' : 'text-gray-400'

            return (
              <div key={stage.key} className="flex items-center gap-2">
                <span
                  className={`w-3.5 h-3.5 rounded-full flex items-center justify-center text-[10px] text-white ${statusClass}`}
                >
                  {isDone ? '✓' : ''}
                </span>
                <span className={`text-xs ${textClass}`}>{stage.label}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default function MessageList({ messages, isLoading, loadingMeta }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading, loadingMeta?.currentStage])

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-5">
      {messages.length === 0 && !isLoading && (
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-300 text-sm select-none">向我提问吧，我会从知识库中寻找答案</p>
        </div>
      )}

      {messages.map((message, idx) => (
        <MessageBubble key={idx} message={message} />
      ))}

      {isLoading && <ThinkingStatus loadingMeta={loadingMeta} />}
      <div ref={bottomRef} />
    </div>
  )
}
