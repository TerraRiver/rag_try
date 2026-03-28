import { useState } from 'react'
import ChatContainer from './components/ChatContainer'

const STAGE_ORDER = [
  { key: 'queued', label: '请求已接收' },
  { key: 'rewrite', label: '理解问题' },
  { key: 'retrieve', label: '检索资料' },
  { key: 'generate', label: '生成答案' },
  { key: 'sources', label: '整理来源' },
]

function App() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [loadingMeta, setLoadingMeta] = useState(null)

  const updateAssistantMessage = (assistantId, updater, fallbackMessage = null) => {
    setMessages((prev) =>
      {
        let matched = false
        const next = prev.map((message) => {
          if (message.id !== assistantId) return message
          matched = true
          return updater(message)
        })
        if (!matched && fallbackMessage) {
          next.push(fallbackMessage)
        }
        return next
      }
    )
  }

  const sendMessage = async (query) => {
    if (!query.trim() || isLoading) return

    const userMessage = { id: `user-${Date.now()}`, role: 'user', content: query }
    const assistantId = `assistant-${Date.now()}`
    const history = messages.map((msg) => ({ role: msg.role, content: msg.content }))

    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantId, role: 'assistant', content: '', sources: [], isStreaming: true },
    ])
    setIsLoading(true)
    setLoadingMeta({
      startedAt: Date.now(),
      currentStage: 'queued',
      stages: [],
      stageOrder: STAGE_ORDER,
    })

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, history }),
      })

      if (!response.ok) {
        const err = await response.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${response.status}`)
      }

      if (!response.body) {
        throw new Error('流式响应不可用')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      let finalPayload = null
      let streamError = null

      const consumeEvent = (event) => {
        if (event.type === 'stage') {
          setLoadingMeta((prev) => {
            if (!prev) return prev
            const stageExists = prev.stages.some((stage) => stage.key === event.stage)
            const nextStages = stageExists
              ? prev.stages.map((stage) =>
                  stage.key === event.stage
                    ? { ...stage, label: event.label || stage.label }
                    : stage
                )
              : [
                  ...prev.stages,
                  {
                    key: event.stage,
                    label: event.label || event.stage,
                    elapsedMs: event.elapsed_ms ?? Date.now() - prev.startedAt,
                  },
                ]

            return {
              ...prev,
              currentStage: event.stage || prev.currentStage,
              stages: nextStages,
            }
          })
          return
        }

        if (event.type === 'delta') {
          const token = event.delta || ''
          if (!token) return
          updateAssistantMessage(assistantId, (message) => ({
            ...message,
            content: (message.content || '') + token,
          }))
          return
        }

        if (event.type === 'final') {
          finalPayload = {
            answer: event.answer || '',
            source_nodes: event.source_nodes || [],
          }
          return
        }

        if (event.type === 'error') {
          streamError = event.error || '请求失败'
        }
      }

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        lines.forEach((line) => {
          const trimmed = line.trim()
          if (!trimmed) return
          try {
            consumeEvent(JSON.parse(trimmed))
          } catch (_) {
            // Ignore malformed line and keep stream alive.
          }
        })
      }

      buffer += decoder.decode()
      if (buffer.trim()) {
        try {
          consumeEvent(JSON.parse(buffer.trim()))
        } catch (_) {
          // Ignore malformed trailing line.
        }
      }

      if (streamError) {
        throw new Error(streamError)
      }

      if (!finalPayload) {
        throw new Error('响应提前结束，未收到最终结果')
      }

      updateAssistantMessage(assistantId, (message) => ({
        ...message,
        content: finalPayload.answer || message.content,
        sources: finalPayload.source_nodes,
        isStreaming: false,
      }))
    } catch (error) {
      const errorMessage = {
        id: assistantId,
        role: 'assistant',
        content: `请求失败：${error.message}`,
        sources: [],
        isStreaming: false,
      }
      updateAssistantMessage(assistantId, () => errorMessage, errorMessage)
    } finally {
      setIsLoading(false)
      setLoadingMeta(null)
    }
  }

  return (
    <ChatContainer
      messages={messages}
      isLoading={isLoading}
      loadingMeta={loadingMeta}
      stageOrder={STAGE_ORDER}
      onSend={sendMessage}
    />
  )
}

export default App
