import { useEffect, useRef, useState } from 'react'

export default function ChatInput({ onSend, isLoading, isRestoring = false }) {
  const [value, setValue] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const textareaRef = useRef(null)
  const isBusy = isLoading || isRestoring
  const collapsedMobileHeight = 56
  const expandedMobileHeight = 88
  const desktopMinHeight = 96

  const resizeTextarea = (nextValue, focused = isFocused) => {
    const ta = textareaRef.current
    if (!ta) return

    ta.style.height = 'auto'

    const minHeight = window.innerWidth >= 768
      ? desktopMinHeight
      : focused
        ? expandedMobileHeight
        : collapsedMobileHeight

    if (!nextValue.trim()) {
      ta.style.height = `${minHeight}px`
      return
    }

    ta.style.height = `${Math.max(minHeight, Math.min(ta.scrollHeight, 160))}px`
  }

  useEffect(() => {
    resizeTextarea(value, false)
  }, [])

  const handleSend = () => {
    if (!value.trim() || isBusy) return
    onSend(value.trim())
    setValue('')
    resizeTextarea('', false)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e) => {
    const nextValue = e.target.value
    setValue(nextValue)
    resizeTextarea(nextValue, true)
  }

  const handleFocus = () => {
    setIsFocused(true)
    resizeTextarea(value, true)
  }

  const handleBlur = () => {
    setIsFocused(false)
    resizeTextarea(value, false)
  }

  return (
    <div className="border-t border-[color:var(--line)] bg-[color:var(--panel)] px-3 py-3 md:px-8 md:py-6">
      <div className="mx-auto max-w-4xl">
        <div className="rounded-[20px] border border-[color:var(--line)] bg-[color:var(--surface)] p-2.5 shadow-[0_10px_32px_rgba(15,23,42,0.05)] transition-all duration-200 md:rounded-[24px] md:p-3">
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
                onFocus={handleFocus}
                onBlur={handleBlur}
                placeholder={isRestoring ? '正在恢复历史会话…' : '输入你的问题'}
                disabled={isBusy}
                rows={1}
                className={`max-h-[160px] w-full resize-none rounded-[16px] border border-[color:var(--line)] bg-white px-4 py-3 text-[14px] leading-6 text-[color:var(--ink)] outline-none transition-all duration-200 placeholder:text-[color:var(--muted)] focus:border-[color:var(--accent)] focus:ring-4 focus:ring-[color:var(--accent-soft)] disabled:cursor-not-allowed disabled:bg-[color:var(--surface-soft)] md:max-h-[180px] md:rounded-[18px] md:text-[15px] md:leading-7 ${
                  isFocused ? 'min-h-[88px]' : 'min-h-[56px]'
                } md:min-h-[96px]`}
              />
            </div>

            <button
              onClick={handleSend}
              disabled={!value.trim() || isBusy}
              className="flex h-11 w-full items-center justify-center rounded-[14px] border border-[color:var(--accent)] bg-[color:var(--accent)] px-5 text-sm font-semibold text-white transition hover:bg-[color:var(--accent-strong)] disabled:cursor-not-allowed disabled:border-[color:var(--line)] disabled:bg-[color:var(--surface-soft)] disabled:text-[color:var(--muted)] md:h-12 md:min-w-[124px] md:w-auto md:rounded-[16px]"
            >
              {isLoading ? '处理中...' : isRestoring ? '恢复中...' : '发送问题'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
