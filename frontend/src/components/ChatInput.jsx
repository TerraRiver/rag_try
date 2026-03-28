import { useState, useRef } from 'react'

export default function ChatInput({ onSend, isLoading, isRestoring = false }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)
  const isBusy = isLoading || isRestoring

  const handleSend = () => {
    if (!value.trim() || isBusy) return
    onSend(value.trim())
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e) => {
    setValue(e.target.value)
    // 自动撑高 textarea
    const ta = textareaRef.current
    if (ta) {
      ta.style.height = 'auto'
      ta.style.height = Math.min(ta.scrollHeight, 120) + 'px'
    }
  }

  return (
    <div className="border-t border-[color:var(--line)] bg-[color:var(--panel)] px-4 py-4 md:px-8 md:py-6">
      <div className="mx-auto max-w-4xl">
        <div className="rounded-[24px] border border-[color:var(--line)] bg-[color:var(--surface)] p-3 shadow-[0_10px_32px_rgba(15,23,42,0.05)]">
          <div className="flex flex-col gap-3 md:flex-row md:items-end">
            <div className="flex-1">
              <div className="mb-2 flex items-center justify-between gap-3 px-1">
                <span className="section-label">输入问题</span>
                <span className="text-[11px] uppercase tracking-[0.26em] text-[color:var(--muted)]">
                  {isLoading ? 'Generating' : isRestoring ? 'Restoring' : 'Ready'}
                </span>
              </div>
              <textarea
                ref={textareaRef}
                value={value}
                onChange={handleInput}
                onKeyDown={handleKeyDown}
                placeholder={isRestoring ? '正在恢复历史会话…' : '输入你的问题'}
                disabled={isBusy}
                rows={1}
                className="w-full resize-none rounded-[18px] border border-[color:var(--line)] bg-white px-4 py-3 text-[15px] leading-7 text-[color:var(--ink)] outline-none transition placeholder:text-[color:var(--muted)] focus:border-[color:var(--accent)] focus:ring-4 focus:ring-[color:var(--accent-soft)] disabled:cursor-not-allowed disabled:bg-[color:var(--surface-soft)]"
                style={{ minHeight: '96px', maxHeight: '180px' }}
              />
            </div>

            <button
              onClick={handleSend}
              disabled={!value.trim() || isBusy}
              className="flex h-12 min-w-[124px] items-center justify-center rounded-[16px] border border-[color:var(--accent)] bg-[color:var(--accent)] px-5 text-sm font-semibold text-white transition hover:bg-[color:var(--accent-strong)] disabled:cursor-not-allowed disabled:border-[color:var(--line)] disabled:bg-[color:var(--surface-soft)] disabled:text-[color:var(--muted)]"
            >
              {isLoading ? '处理中...' : isRestoring ? '恢复中...' : '发送问题'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
