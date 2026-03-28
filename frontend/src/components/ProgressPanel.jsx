import { useEffect, useMemo, useState } from 'react'

function formatElapsed(ms) {
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, '0')
  const seconds = String(totalSeconds % 60).padStart(2, '0')
  return `${minutes}:${seconds}`
}

export default function ProgressPanel({ loadingMeta, isLoading, stageOrder = [] }) {
  const [now, setNow] = useState(Date.now())

  useEffect(() => {
    if (!isLoading) return undefined
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [isLoading])

  const visibleStageOrder = loadingMeta?.stageOrder || stageOrder
  const currentStage = loadingMeta?.currentStage
  const currentIndex = visibleStageOrder.findIndex((stage) => stage.key === currentStage)
  const elapsedText = useMemo(() => {
    if (!loadingMeta?.startedAt || !isLoading) return '00:00'
    return formatElapsed(Math.max(0, now - loadingMeta.startedAt))
  }, [isLoading, loadingMeta?.startedAt, now])

  return (
    <div className="flex h-full flex-col rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface)] p-5 shadow-[0_10px_28px_rgba(15,23,42,0.05)]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="section-label">进度展示</p>
          <h3 className="mt-2 text-lg font-semibold text-[color:var(--ink)]">检索与生成流程</h3>
        </div>
        <span className="rounded-full border border-[color:var(--line)] bg-[color:var(--surface-soft)] px-3 py-1.5 font-mono text-xs text-[color:var(--muted)]">
          {elapsedText}
        </span>
      </div>

      <p className="mt-3 text-sm leading-6 text-[color:var(--muted)]">
        {isLoading
          ? '当前正在处理你的请求，下面会实时显示阶段推进。'
          : '当前为空闲状态。发送问题后，这里会展示理解、检索和生成进度。'}
      </p>

      <div className="mt-5 flex-1 space-y-2.5">
        {visibleStageOrder.map((stage, index) => {
          const isCurrent = isLoading && index === currentIndex
          const isDone = isLoading && currentIndex > index
          const statusClass = isDone
            ? 'bg-[color:var(--accent)] text-white'
            : isCurrent
              ? 'bg-[color:var(--accent)] text-white pulse-soft'
              : 'bg-[color:var(--surface-soft)] text-[color:var(--muted)]'

          return (
            <div
              key={stage.key}
              className={`rounded-[18px] border px-3 py-3 transition ${
                isCurrent
                  ? 'border-[color:var(--accent-soft)] bg-[color:var(--accent-tint)]'
                  : 'border-[color:var(--line)] bg-white'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className={`flex h-7 w-7 items-center justify-center rounded-full text-[11px] font-semibold ${statusClass}`}>
                  {isDone ? '✓' : `0${index + 1}`}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-[color:var(--ink)]">{stage.label}</p>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[color:var(--surface-soft)]">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        isDone ? 'w-full bg-[color:var(--accent)]' : isCurrent ? 'w-2/3 bg-[color:var(--accent)]' : 'w-0'
                      }`}
                    />
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
