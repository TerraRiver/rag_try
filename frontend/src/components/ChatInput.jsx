import { useState, useRef } from 'react'

export default function ChatInput({ onSend, isLoading }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  const handleSend = () => {
    if (!value.trim() || isLoading) return
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
    <div className="bg-white border-t px-4 py-3 flex-shrink-0">
      <div className="max-w-3xl mx-auto flex items-end gap-2">
        {/* 输入框 */}
        <div className="flex-1">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="输入问题，按 Enter 发送（Shift+Enter 换行）"
            disabled={isLoading}
            rows={1}
            className="w-full resize-none rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 disabled:bg-gray-50 disabled:text-gray-400 transition"
            style={{ minHeight: '44px', maxHeight: '120px' }}
          />
        </div>

        {/* 发送按钮 */}
        <button
          onClick={handleSend}
          disabled={!value.trim() || isLoading}
          className="h-11 px-5 bg-blue-500 text-white rounded-xl text-sm font-medium hover:bg-blue-600 active:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition flex-shrink-0"
        >
          发送
        </button>
      </div>
    </div>
  )
}
