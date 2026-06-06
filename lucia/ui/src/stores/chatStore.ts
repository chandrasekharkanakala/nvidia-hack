import { create } from "zustand";
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
}

export const useChatStore = create<ChatState>((set, get) => ({
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
    set({ activeSessionId: id });
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
}));
