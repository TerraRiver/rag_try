import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'

export default function MessageList({ messages, isLoading }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-5">
      {/* 空状态提示 */}
      {messages.length === 0 && !isLoading && (
        <div className="flex items-center justify-center h-full">
          <p className="text-gray-300 text-sm select-none">向我提问吧，我会从知识库中寻找答案</p>
        </div>
      )}

      {/* 消息气泡 */}
      {messages.map((msg, idx) => (
        <MessageBubble key={idx} message={msg} />
      ))}

      {/* 思考中动画 */}
      {isLoading && (
        <div className="flex items-start gap-2">
          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-bold text-xs flex-shrink-0">
            AI
          </div>
          <div className="bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-gray-100">
            <div className="flex items-center gap-1.5">
              <span className="text-gray-400 text-sm">思考中</span>
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
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
