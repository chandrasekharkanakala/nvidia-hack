export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  mode: AgentMode
  timestamp: string
  image?: string // base64
  chart?: string // base64 PNG from visualizer
  metrics?: MessageMetrics
  toolCalls?: ToolCallEvent[]
}

export type AgentMode = "light" | "deep"

export interface Session {
  id: string
  title: string // first message truncated
  lastActivity: string
  messageCount: number
}

export interface MessageMetrics {
  latencyMs: number
  timeToFirstTokenMs: number
  tokensPrompt: number
  tokensCompletion: number
  toolsUsed: string[]
  confidence?: number
}

export interface ToolCallEvent {
  tool: string
  description: string
  durationMs: number
  success: boolean
}

// WebSocket protocol
export type WSIncoming =
  | { type: "thinking" }
  | { type: "tool_start"; tool: string; description: string }
  | { type: "tool_end"; tool: string; duration_ms: number; success: boolean }
  | { type: "token"; content: string }
  | { type: "chart"; data: string }
  | { type: "done"; metrics: MessageMetrics }
  | { type: "error"; message: string }

export interface WSOutgoing {
  type: "message"
  content: string
  mode: AgentMode
  session_id: string
  image?: string // base64
}

export interface SystemMetrics {
  totalRequests: number
  avgLatencyMs: number
  avgTokens: number
  gpuMemoryUsedGb: number
  gpuMemoryTotalGb: number
  toolSuccessRates: Record<string, number>
}
