import { useState, useEffect, useRef } from "react"
import { SendHorizontal, Loader2, PanelLeftOpen, StopCircle, RefreshCw } from "lucide-react"
import ReactMarkdown from "react-markdown"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism"
import remarkGfm from "remark-gfm"
import axios from "axios"
import { useChatScroll } from "@/hooks/use-chat-scroll"
import { cn } from "@/lib/utils"

export function ChatArea({ sessionId, wsUrl, onSessionUpdate, sidebarOpen, toggleSidebar }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState(null)
  const wsRef = useRef(null)
  const scrollRef = useRef(null)
  
  useChatScroll(scrollRef, messages)

  // Fetch session history when sessionId changes
  useEffect(() => {
    if (!sessionId) {
      setMessages([])
      return
    }

    const fetchSession = async () => {
      try {
        const res = await axios.get(`/api/session?session_id=${sessionId}`)
        setMessages(res.data.history || [])
        setError(null)
      } catch (err) {
        if (err.response && err.response.status === 404) {
          // New session not yet created on backend
          setMessages([])
          setError(null)
        } else {
          console.error("Failed to load session", err)
          setError("Could not load chat history.")
        }
      }
    }
    fetchSession()
  }, [sessionId])

  // Cleanup WS on unmount or session change
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [sessionId])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || isStreaming) return

    const prompt = input.trim()
    setInput("")
    setError(null)

    // Optimistic update
    const newMessages = [...messages, { role: "user", content: prompt }]
    setMessages(newMessages)
    setIsStreaming(true)

    // Prepare assistant placeholder
    setMessages(prev => [...prev, { role: "assistant", content: "" }])

    try {
      if (!sessionId) {
        throw new Error("No session ID active")
      }

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        // Just send the prompt. Session start is handled by App.jsx or implicitly by backend.
        ws.send(JSON.stringify({
          prompt,
          max_tokens: 2048,
          session_id: sessionId,
          include_history: true,
          history_window: 10
        }))
      }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        
        if (data.type === "token") {
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last.role === "assistant") {
              return [...prev.slice(0, -1), { ...last, content: last.content + data.content }]
            }
            return prev
          })
        } else if (data.type === "end") {
          setIsStreaming(false)
          ws.close()
          onSessionUpdate() // Refresh list title
        } else if (data.type === "error") {
          setError(data.detail || "Unknown error")
          setIsStreaming(false)
          ws.close()
        }
      }

      ws.onerror = (e) => {
        console.error("WebSocket error", e)
        setError("Connection failed. Check if HalaAI server is running.")
        setIsStreaming(false)
      }

      ws.onclose = () => {
        setIsStreaming(false)
      }

    } catch (err) {
      setError(err.message)
      setIsStreaming(false)
    }
  }

  const stopGeneration = () => {
    if (wsRef.current) {
      wsRef.current.close()
      setIsStreaming(false)
      onSessionUpdate()
    }
  }

  return (
    <div className="flex flex-col h-full relative">
      {/* Header / Top Bar */}
      <div className="absolute top-0 left-0 right-0 p-4 flex items-center justify-between z-10 bg-gradient-to-b from-background to-transparent pointer-events-none">
        <div className="flex items-center gap-2 pointer-events-auto">
          {!sidebarOpen && (
            <button 
              onClick={toggleSidebar}
              className="p-2 rounded-md hover:bg-accent text-muted-foreground"
            >
              <PanelLeftOpen size={20} />
            </button>
          )}
          <div className="font-semibold text-lg opacity-90">HalaAI</div>
          <div className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">Beta</div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 md:px-0 pt-20 pb-4 scroll-smooth" ref={scrollRef}>
        <div className="max-w-3xl mx-auto space-y-8">
          {messages.length === 0 && (
             <div className="flex flex-col items-center justify-center h-[50vh] text-center opacity-40">
                <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
                  <div className="w-8 h-8 rounded-full bg-primary animate-pulse" />
                </div>
                <h2 className="text-xl font-medium mb-2">How can I help you today?</h2>
             </div>
          )}
          
          {messages.map((msg, i) => (
            <div key={i} className={cn("flex gap-4 group", msg.role === "user" ? "justify-end" : "justify-start")}>
              {msg.role === "assistant" && (
                 <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary to-accent flex-shrink-0 flex items-center justify-center text-[10px] text-white font-bold shadow-sm mt-1">
                   AI
                 </div>
              )}
              
              <div className={cn(
                "relative max-w-[85%] md:max-w-[75%] rounded-2xl px-5 py-3.5 shadow-sm text-sm leading-relaxed",
                msg.role === "user" 
                  ? "bg-accent text-accent-foreground rounded-tr-sm" 
                  : "bg-card border border-border/50 text-card-foreground rounded-tl-sm"
              )}>
                {msg.role === "user" ? (
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                ) : (
                  <div className="markdown-body">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        code({node, inline, className, children, ...props}) {
                          const match = /language-(\w+)/.exec(className || '')
                          return !inline && match ? (
                            <SyntaxHighlighter
                              {...props}
                              style={oneDark}
                              language={match[1]}
                              PreTag="div"
                              customStyle={{ margin: 0, borderRadius: '0.5rem', fontSize: '0.8rem' }}
                            >
                              {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                          ) : (
                            <code {...props} className={cn("bg-muted px-1.5 py-0.5 rounded text-xs font-mono", className)}>
                              {children}
                            </code>
                          )
                        }
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>

               {msg.role === "user" && (
                 <div className="w-8 h-8 rounded-full bg-secondary flex-shrink-0 flex items-center justify-center text-secondary-foreground text-xs font-medium mt-1">
                   You
                 </div>
              )}
            </div>
          ))}

          {error && (
            <div className="flex justify-center p-4">
              <div className="bg-destructive/10 text-destructive px-4 py-2 rounded-lg text-sm flex items-center gap-2 border border-destructive/20">
                <span className="font-semibold">Error:</span> {error}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="p-4 bg-background/80 backdrop-blur-md border-t border-border/50">
        <div className="max-w-3xl mx-auto relative">
          <form onSubmit={handleSubmit} className="relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSubmit(e)
                }
              }}
              placeholder="Message HalaAI..."
              className="w-full bg-accent/50 border border-border rounded-xl pl-4 pr-14 py-4 min-h-[56px] max-h-[200px] resize-none focus:outline-none focus:ring-1 focus:ring-primary/50 text-sm scrollbar-hide shadow-sm transition-all focus:bg-background"
              rows={1}
              style={{ height: "auto", overflow: "hidden" }}
              onInput={(e) => {
                e.target.style.height = 'auto'
                e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`
              }}
            />
            <div className="absolute right-2 bottom-2.5 flex gap-2">
               {isStreaming ? (
                  <button 
                    type="button" 
                    onClick={stopGeneration}
                    className="p-2 rounded-lg bg-destructive hover:bg-destructive/90 text-white transition-colors shadow-sm"
                  >
                    <StopCircle size={18} fill="currentColor" />
                  </button>
               ) : (
                  <button 
                    type="submit" 
                    disabled={!input.trim()}
                    className="p-2 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
                  >
                    {isStreaming ? <Loader2 size={18} className="animate-spin" /> : <SendHorizontal size={18} />}
                  </button>
               )}
            </div>
          </form>
          <div className="text-center mt-2 text-[10px] text-muted-foreground opacity-60">
            HalaAI can make mistakes. Consider checking important information.
          </div>
        </div>
      </div>
    </div>
  )
}