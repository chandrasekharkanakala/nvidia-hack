import { useEffect, useRef } from "react";
import { useChatStore } from "../stores/chatStore";
import { useMetricsStore } from "../stores/metricsStore";
import type { WSIncoming } from "../types";

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const { addToken, setToolCall, setStreaming, finishMessage, startThinking, updateLastAssistantMessage } =
    useChatStore.getState();
  const metricsUpdate = useMetricsStore.getState().update;

  useEffect(() => {
    function connect() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[WS] Connected");
      };

      ws.onmessage = (event) => {
        const data: WSIncoming = JSON.parse(event.data);

        switch (data.type) {
          case "thinking":
            startThinking();
            break;

          case "tool_start":
            setToolCall({ tool: data.tool, description: data.description });
            break;

          case "tool_end": {
            setToolCall(null);
            const state = useChatStore.getState();
            const msgs = [...state.messages];
            const last = msgs[msgs.length - 1];
            if (last && last.role === "assistant") {
              const toolCalls = [...(last.toolCalls || [])];
              toolCalls.push({
                tool: data.tool,
                description: "",
                durationMs: data.duration_ms,
                success: data.success,
              });
              updateLastAssistantMessage({ toolCalls });
            }
            break;
          }

          case "token":
            addToken(data.content);
            break;

          case "done":
            finishMessage(data.metrics);
            metricsUpdate({
              latency: data.metrics.latencyMs,
              tokens: data.metrics.tokensCompletion,
            });
            break;

          case "error":
            setStreaming(false);
            setToolCall(null);
            addToken(`\n\n⚠️ Error: ${data.message}`);
            break;
        }
      };

      ws.onclose = () => {
        console.log("[WS] Disconnected, reconnecting...");
        reconnectTimer.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);

  return wsRef;
}
