import MessageList from './MessageList'
import ChatInput from './ChatInput'

export default function ChatContainer({ messages, isLoading, loadingMeta, onSend }) {
  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-3 shadow-sm flex-shrink-0">
        <h1 className="text-base font-semibold text-gray-800">RAG 知识库问答</h1>
        <p className="text-xs text-gray-400 mt-0.5">基于本地知识库 · 由硅基流动大模型驱动</p>
      </header>

      <MessageList messages={messages} isLoading={isLoading} loadingMeta={loadingMeta} />
      <ChatInput onSend={onSend} isLoading={isLoading} />
    </div>
  )
}
