import { create } from "zustand";
import { persist } from "zustand/middleware";
import { getGlobalWs } from "../lib/wsRef";
import type { Message, Session, AgentMode, MessageMetrics } from "../types";

interface ChatState {
  sessions: Session[];
  activeSessionId: string | null;
  messages: Message[];
  isStreaming: boolean;
  currentToolCall: { tool: string; description: string } | null;
  mode: AgentMode;

  sendMessage: (content: string, image?: string) => void;
  setMode: (mode: AgentMode) => void;
  createSession: () => void;
  loadSession: (id: string) => void;
  setSessions: (sessions: Session[]) => void;
  addToken: (token: string) => void;
  setToolCall: (toolCall: { tool: string; description: string } | null) => void;
  setStreaming: (streaming: boolean) => void;
  addMessage: (message: Message) => void;
  updateLastAssistantMessage: (update: Partial<Message>) => void;
  finishMessage: (metrics: MessageMetrics) => void;
  startThinking: () => void;
  fetchSessions: () => Promise<void>;
  fetchMessages: (sessionId: string) => Promise<void>;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: [],
  isStreaming: false,
  currentToolCall: null,
  mode: "light",

  sendMessage: (content: string, image?: string) => {
    const state = get();
    let sessionId = state.activeSessionId;

    if (!sessionId) {
      sessionId = crypto.randomUUID();
      const newSession: Session = {
        id: sessionId,
        title: content.slice(0, 50),
        lastActivity: new Date().toISOString(),
        messageCount: 0,
      };
      set({ activeSessionId: sessionId, sessions: [newSession, ...state.sessions] });
    }

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      mode: state.mode,
      timestamp: new Date().toISOString(),
      image,
    };

    set((s) => ({ messages: [...s.messages, userMessage], isStreaming: true }));

    // Send over WebSocket
    const ws = getGlobalWs();
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: "message",
        content,
        mode: state.mode,
        session_id: sessionId,
        image,
      }));
    } else {
      console.warn("[Chat] WebSocket not connected, message not sent");
      set({ isStreaming: false });
    }
  },

  setMode: (mode) => set({ mode }),

  createSession: () => {
    set({ activeSessionId: null, messages: [] });
  },

  loadSession: (id) => {
    set({ activeSessionId: id, messages: [] });
    // Fetch messages from backend
    get().fetchMessages(id);
  },

  setSessions: (sessions) => set({ sessions }),

  addToken: (token) => {
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content: last.content + token };
      } else {
        msgs.push({
          id: crypto.randomUUID(),
          role: "assistant",
          content: token,
          mode: state.mode,
          timestamp: new Date().toISOString(),
          toolCalls: [],
        });
      }
      return { messages: msgs };
    });
  },

  setToolCall: (toolCall) => set({ currentToolCall: toolCall }),

  setStreaming: (streaming) => set({ isStreaming: streaming }),

  addMessage: (message) => set((s) => ({ messages: [...s.messages, message] })),

  updateLastAssistantMessage: (update) => {
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, ...update };
      }
      return { messages: msgs };
    });
  },

  finishMessage: (metrics) => {
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, metrics };
      }
      return { messages: msgs, isStreaming: false, currentToolCall: null };
    });
  },

  startThinking: () => {
    set((state) => {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (!last || last.role !== "assistant") {
        msgs.push({
          id: crypto.randomUUID(),
          role: "assistant",
          content: "",
          mode: state.mode,
          timestamp: new Date().toISOString(),
          toolCalls: [],
        });
      }
      return { messages: msgs };
    });
  },

  fetchSessions: async () => {
    try {
      const res = await fetch("/sessions");
      if (res.ok) {
        const data = await res.json();
        const raw = data.sessions || data;
        const sessions = raw.map((s: Record<string, unknown>) => ({
          id: s.id,
          title: s.title || "",
          lastActivity: s.lastActivity || s.last_activity || new Date().toISOString(),
          messageCount: s.messageCount ?? s.message_count ?? 0,
        }));
        set({ sessions });
      }
    } catch {
      // Backend may not be available yet
    }
  },

  fetchMessages: async (sessionId: string) => {
    try {
      const res = await fetch(`/sessions/${sessionId}/messages`);
      if (res.ok) {
        const data = await res.json();
        const messages = data.messages || data;
        set({ messages, activeSessionId: sessionId });
      }
    } catch {
      // Backend may not be available
    }
  },
}),
    {
      name: "lucia-chat-store",
      partialize: (state) => ({
        sessions: state.sessions,
        activeSessionId: state.activeSessionId,
        messages: state.messages,
        mode: state.mode,
      }),
    }
  )
);
