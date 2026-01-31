import { useState, useEffect, useRef } from 'react'
import { Sidebar } from './components/Sidebar'
import { ChatArea } from './components/ChatArea'
import { v4 as uuidv4 } from 'uuid'
import axios from 'axios'

function App() {
  const [sessions, setSessions] = useState([])
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  
  // Dynamically determine WS URL based on current host (handles dev proxy & prod)
  const getWsUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws/chat/v2`
  }
  
  const [wsUrl, setWsUrl] = useState(getWsUrl())

  useEffect(() => {
    // We don't necessarily need /config anymore if we use relative paths
    // but we'll keep the pattern if needed for specific overrides.
    // For now, rely on the proxy.
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      const res = await axios.get('/api/sessions')
      const sorted = (res.data || []).sort((a, b) => {
        const da = new Date(a.updated_at || a.last_active_at || 0)
        const db = new Date(b.updated_at || b.last_active_at || 0)
        return db - da
      })
      setSessions(sorted)
    } catch (err) {
      console.error("Failed to load sessions", err)
    }
  }

  const startSessionBackend = (id) => {
    // Fire-and-forget session start to ensure backend knows about it
    // This matches the old app's behavior
    try {
      const ws = new WebSocket(wsUrl)
      ws.onopen = () => {
        ws.send(JSON.stringify({ type: "session_start", session_id: id }))
        setTimeout(() => ws.close(), 100)
      }
      ws.onerror = (e) => console.warn("Session start WS warning", e)
    } catch (e) {
      console.error("Failed to start session on backend", e)
    }
  }

  const createSession = () => {
    const newId = uuidv4()
    setCurrentSessionId(newId)
    startSessionBackend(newId)
  }

  const deleteSession = async (id) => {
    if (!confirm("Are you sure?")) return
    try {
      await axios.delete(`/api/session?session_id=${id}`)
      await loadSessions()
      if (currentSessionId === id) {
        setCurrentSessionId(null)
      }
    } catch (err) {
      console.error("Failed to delete session", err)
    }
  }

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden">
      <Sidebar 
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={setCurrentSessionId}
        onCreateSession={createSession}
        onDeleteSession={deleteSession}
        isOpen={sidebarOpen}
        toggleOpen={() => setSidebarOpen(!sidebarOpen)}
      />
      <main className="flex-1 h-full relative flex flex-col min-w-0">
        <ChatArea 
          sessionId={currentSessionId} 
          wsUrl={wsUrl} 
          onSessionUpdate={loadSessions}
          sidebarOpen={sidebarOpen}
          toggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        />
      </main>
    </div>
  )
}

export default App