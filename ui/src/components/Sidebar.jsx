import { Plus, MessageSquare, Trash2, PanelLeftClose, PanelLeftOpen, Moon, Sun } from "lucide-react"
import { cn } from "@/lib/utils"
import { useEffect, useState } from "react"

export function Sidebar({ 
  sessions, 
  currentSessionId, 
  onSelectSession, 
  onCreateSession, 
  onDeleteSession,
  isOpen,
  toggleOpen
}) {
  const [theme, setTheme] = useState("dark")

  useEffect(() => {
    const isDark = document.documentElement.classList.contains("dark")
    setTheme(isDark ? "dark" : "light")
  }, [])

  const toggleTheme = () => {
    const root = document.documentElement
    if (theme === "dark") {
      root.classList.remove("dark")
      setTheme("light")
    } else {
      root.classList.add("dark")
      setTheme("dark")
    }
  }

  if (!isOpen) {
    return (
      <div className="absolute left-4 top-4 z-50 md:hidden">
        <button 
          onClick={toggleOpen}
          className="p-2 rounded-md hover:bg-accent/50 text-muted-foreground"
        >
          <PanelLeftOpen size={20} />
        </button>
      </div>
    )
  }

  return (
    <div className={cn(
      "flex-col w-[260px] h-full bg-card border-r border-border transition-all duration-300 ease-in-out absolute md:relative z-40",
      isOpen ? "flex translate-x-0" : "hidden -translate-x-full md:flex md:-ml-[260px]"
    )}>
      {/* Header */}
      <div className="p-3 flex items-center justify-between">
        <button 
          onClick={onCreateSession}
          className="flex-1 flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md hover:bg-accent transition-colors border border-border/50 shadow-sm"
        >
          <Plus size={16} />
          New Chat
        </button>
        <button 
          onClick={toggleOpen}
          className="ml-2 p-2 rounded-md hover:bg-accent text-muted-foreground md:hidden"
        >
          <PanelLeftClose size={18} />
        </button>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1 scrollbar-thin">
        <div className="text-xs font-semibold text-muted-foreground px-2 py-2">Recents</div>
        {sessions.map((session) => (
          <div 
            key={session.id}
            className={cn(
              "group flex items-center gap-3 px-3 py-3 text-sm rounded-lg cursor-pointer transition-colors relative",
              currentSessionId === session.id 
                ? "bg-accent text-accent-foreground" 
                : "hover:bg-accent/50 text-muted-foreground hover:text-foreground"
            )}
            onClick={() => onSelectSession(session.id)}
          >
            <MessageSquare size={16} className="shrink-0" />
            <div className="flex-1 truncate pr-6">
              {session.title || "New Conversation"}
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDeleteSession(session.id)
              }}
              className="absolute right-2 opacity-0 group-hover:opacity-100 p-1 hover:text-destructive transition-opacity"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-border mt-auto">
        <button 
          onClick={toggleTheme}
          className="flex items-center gap-3 px-3 py-2 w-full text-sm font-medium rounded-md hover:bg-accent text-muted-foreground transition-colors"
        >
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          {theme === "dark" ? "Light Mode" : "Dark Mode"}
        </button>
      </div>
    </div>
  )
}
