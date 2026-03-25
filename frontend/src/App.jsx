import { useState } from 'react'
import ChatContainer from './components/ChatContainer'

function App() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  const sendMessage = async (query) => {
    if (!query.trim() || isLoading) return

    const userMessage = { role: 'user', content: query }
    const history = messages.map((m) => ({ role: m.role, content: m.content }))

    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, history }),
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${response.status}`)
      }

      const data = await response.json()
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.answer, sources: data.source_nodes || [] },
      ])
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `请求失败：${error.message}`, sources: [] },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return <ChatContainer messages={messages} isLoading={isLoading} onSend={sendMessage} />
}

export default App
