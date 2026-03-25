import ReactMarkdown from 'react-markdown'

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex items-start gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* 头像 */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
          isUser ? 'bg-blue-500 text-white' : 'bg-blue-100 text-blue-600'
        }`}
      >
        {isUser ? '我' : 'AI'}
      </div>

      {/* 内容区 */}
      <div className={`max-w-[75%] flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>
        {/* 气泡 */}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
            isUser
              ? 'bg-blue-500 text-white rounded-tr-sm'
              : 'bg-white text-gray-800 rounded-tl-sm border border-gray-100'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-p:my-1 prose-pre:my-2 prose-code:text-blue-600 prose-code:bg-blue-50 prose-code:px-1 prose-code:rounded">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* 参考来源（折叠展示） */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <details open className="text-xs text-gray-400 w-full">
            <summary className="cursor-pointer hover:text-gray-500 select-none py-0.5">
              参考来源 ({message.sources.length} 条)
            </summary>
            <div className="mt-1 space-y-1.5">
              {message.sources.map((src, i) => {
                // 把后端返回的多行字符串按行渲染，链接行单独变成可点击的 <a>
                const lines = src.split('\n')
                return (
                  <div
                    key={i}
                    className="bg-gray-50 border border-gray-100 rounded-lg px-3 py-2 text-gray-500 leading-relaxed"
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
                              className="text-blue-400 hover:text-blue-600 hover:underline break-all"
                            >
                              🔗 原文链接
                            </a>
                          </div>
                        )
                      }
                      return <div key={j}>{line}</div>
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
