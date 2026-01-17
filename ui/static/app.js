let wsUrl = null;
let currentSessionId = null;
let sessions = [];
let isStreaming = false;

const sessionListEl = document.getElementById("session-list");
const messagesEl = document.getElementById("messages");
const promptEl = document.getElementById("prompt");
const statusEl = document.getElementById("status");
const chatTitleEl = document.querySelector(".chat-title");
const chatSubtitleEl = document.getElementById("chat-subtitle");
const themeToggleEl = document.getElementById("theme-toggle");

function setStatus(text) {
  statusEl.textContent = text;
}

function applyTheme(theme) {
  document.body.dataset.theme = theme;
  localStorage.setItem("hala_theme", theme);
  const icon = themeToggleEl.querySelector(".material-symbols-rounded");
  if (icon) {
    icon.textContent = theme === "light" ? "dark_mode" : "light_mode";
  }
}

function initTheme() {
  const saved = localStorage.getItem("hala_theme");
  if (saved) {
    applyTheme(saved);
    return;
  }
  const prefersLight = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
  applyTheme(prefersLight ? "light" : "dark");
}

function generateSessionId() {
  const safeCrypto = window.crypto;
  if (safeCrypto && typeof safeCrypto.randomUUID === "function") {
    return safeCrypto.randomUUID();
  }
  if (!safeCrypto || typeof safeCrypto.getRandomValues !== "function") {
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
  const fallback = ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(
    /[018]/g,
    (c) =>
      (c ^ (safeCrypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (c / 4)))).toString(16)
  );
  return fallback;
}

function formatTimestamp(value) {
  if (!value) return "";
  try {
    const date = new Date(value);
    return date.toLocaleString();
  } catch (err) {
    return "";
  }
}

function messagePreview(history) {
  if (!Array.isArray(history) || history.length === 0) return "No messages yet";
  const last = history[history.length - 1];
  if (!last) return "";
  const role = last.role === "user" ? "You: " : "Hala: ";
  const content = (last.content || "").trim();
  return role + content.slice(0, 60);
}

function renderSessions() {
  sessionListEl.innerHTML = "";
  if (sessions.length === 0) {
    const empty = document.createElement("div");
    empty.className = "session-preview";
    empty.textContent = "No sessions yet";
    sessionListEl.appendChild(empty);
    return;
  }

  sessions.forEach((session) => {
    const item = document.createElement("div");
    item.className = "session-item";
    if (session.id === currentSessionId) {
      item.classList.add("active");
    }

    const title = document.createElement("div");
    title.className = "session-title";
    title.textContent = session.title || "Conversation";

    const preview = document.createElement("div");
    preview.className = "session-preview";
    const previewText = messagePreview(session.history);
    const ts = formatTimestamp(session.updated_at || session.last_active_at);
    preview.textContent = ts ? `${previewText} • ${ts}` : previewText;

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "session-delete";
    deleteBtn.textContent = "✕";
    deleteBtn.title = "Delete chat";
    deleteBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      removeSession(session.id);
    });

    item.appendChild(title);
    item.appendChild(preview);
    item.appendChild(deleteBtn);
    item.addEventListener("click", () => selectSession(session.id));
    sessionListEl.appendChild(item);
  });
}

function renderMessages(history) {
  messagesEl.innerHTML = "";
  if (!Array.isArray(history) || history.length === 0) {
    const empty = document.createElement("div");
    empty.className = "session-preview";
    empty.textContent = "Start a new conversation.";
    messagesEl.appendChild(empty);
    return;
  }

  history.forEach((msg) => {
    if (!msg || !msg.content) return;
    const bubble = document.createElement("div");
    bubble.className = `message ${msg.role === "user" ? "user" : "assistant"}`;
    bubble.textContent = msg.content;
    messagesEl.appendChild(bubble);
  });
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendMessage(role, content) {
  const firstChild = messagesEl.firstElementChild;
  if (firstChild && firstChild.classList.contains("session-preview")) {
    messagesEl.innerHTML = "";
  }
  const bubble = document.createElement("div");
  bubble.className = `message ${role}`;
  bubble.textContent = content;
  messagesEl.appendChild(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return bubble;
}

async function loadConfig() {
  const resp = await fetch("/config");
  if (!resp.ok) {
    throw new Error("Failed to load config");
  }
  const data = await resp.json();
  wsUrl = data.ws_url;
}

async function fetchSessions() {
  const resp = await fetch("/api/sessions");
  if (!resp.ok) {
    throw new Error("Failed to load sessions");
  }
  const data = await resp.json();
  sessions = Array.isArray(data) ? data : [];
  sessions.sort((a, b) => {
    const aTime = new Date(a.updated_at || a.last_active_at || 0).getTime();
    const bTime = new Date(b.updated_at || b.last_active_at || 0).getTime();
    return bTime - aTime;
  });
  renderSessions();
}

async function refreshSessions(selectCurrent) {
  await fetchSessions();
  if (!sessions.length) {
    if (selectCurrent) {
      await createSession();
    }
    return;
  }
  if (selectCurrent && currentSessionId) {
    const found = sessions.find((s) => s.id === currentSessionId);
    if (found) {
      await selectSession(currentSessionId);
      return;
    }
  }
  if (selectCurrent) {
    await selectSession(sessions[0].id);
  }
}

async function selectSession(sessionId) {
  if (!sessionId) return;
  currentSessionId = sessionId;
  renderSessions();
  const resp = await fetch(`/api/session?session_id=${encodeURIComponent(sessionId)}`);
  if (!resp.ok) {
    throw new Error("Failed to load session");
  }
  const session = await resp.json();
  chatTitleEl.textContent = session.title || "Conversation";
  chatSubtitleEl.textContent = session.updated_at
    ? `Updated ${formatTimestamp(session.updated_at)}`
    : "Local HalaAI engine";
  renderMessages(session.history || []);
}

async function createSession() {
  currentSessionId = generateSessionId();
  chatTitleEl.textContent = "New conversation";
  chatSubtitleEl.textContent = "Local HalaAI engine";
  messagesEl.innerHTML = "";

  if (!wsUrl) return;
  try {
    const ws = new WebSocket(wsUrl);
    ws.addEventListener("open", () => {
      ws.send(JSON.stringify({ type: "session_start", session_id: currentSessionId }));
      ws.close();
    });
  } catch (err) {
    // Session will still be created on first prompt.
  }
}

async function sendMessage(prompt) {
  if (!prompt || isStreaming) return;
  if (!currentSessionId) {
    await createSession();
  }
  if (!wsUrl) {
    appendMessage("assistant", "Error: WebSocket URL not configured.");
    return;
  }
  appendMessage("user", prompt);
  promptEl.value = "";
  promptEl.style.height = "auto";

  const assistantBubble = appendMessage("assistant", "");
  isStreaming = true;

  const payload = {
    prompt,
    max_tokens: 1024,
    session_id: currentSessionId,
    include_history: true,
    history_window: 16,
  };

  try {
    const ws = new WebSocket(wsUrl);
    ws.addEventListener("open", () => {
      ws.send(JSON.stringify(payload));
    });

    ws.addEventListener("message", (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "token") {
        assistantBubble.textContent += data.content || "";
        messagesEl.scrollTop = messagesEl.scrollHeight;
      } else if (data.type === "end") {
        ws.close();
      } else if (data.type === "error") {
        assistantBubble.textContent = `Error: ${data.detail || "Unknown error"}`;
        ws.close();
      }
    });

    ws.addEventListener("close", async () => {
      isStreaming = false;
      await refreshSessions(false);
    });
  } catch (err) {
    assistantBubble.textContent = `Error: ${err}`;
    isStreaming = false;
  }
}

function autoResizeTextarea() {
  promptEl.style.height = "auto";
  promptEl.style.height = `${promptEl.scrollHeight}px`;
}

promptEl.addEventListener("input", autoResizeTextarea);

promptEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    const value = promptEl.value.trim();
    if (value) {
      sendMessage(value);
    }
  }
});

document.getElementById("composer").addEventListener("submit", (event) => {
  event.preventDefault();
  const value = promptEl.value.trim();
  if (value) {
    sendMessage(value);
  }
});

document.getElementById("new-chat").addEventListener("click", async () => {
  await createSession();
  await fetchSessions();
  renderSessions();
});

document.getElementById("refresh-sessions").addEventListener("click", async () => {
  try {
    await refreshSessions(true);
    setStatus("Online");
  } catch (err) {
    setStatus("HalaAI offline");
  }
});

themeToggleEl.addEventListener("click", () => {
  const next = document.body.dataset.theme === "light" ? "dark" : "light";
  applyTheme(next);
});

async function removeSession(sessionId) {
  if (!sessionId) return;
  const confirmed = window.confirm("Delete this chat? This cannot be undone.");
  if (!confirmed) return;

  const resp = await fetch(`/api/session?session_id=${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
  if (!resp.ok) {
    alert("Failed to delete chat.");
    return;
  }
  await refreshSessions(false);
  if (!sessions.length) {
    await createSession();
    return;
  }
  if (sessionId === currentSessionId || !sessions.find((s) => s.id === currentSessionId)) {
    await selectSession(sessions[0].id);
  }
}

async function init() {
  initTheme();
  try {
    await loadConfig();
    setStatus("Online");
  } catch (err) {
    setStatus("Config error");
  }

  try {
    await refreshSessions(true);
  } catch (err) {
    setStatus("HalaAI offline");
  }
}

init();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/sw.js", { scope: "/" }).catch(() => {});
  });
}
