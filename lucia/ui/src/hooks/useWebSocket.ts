import { useEffect, useRef } from "react";
import { useChatStore } from "../stores/chatStore";
import { useMetricsStore } from "../stores/metricsStore";
import { postTTS } from "../lib/api";
import { setGlobalWs } from "../lib/wsRef";
import { useVoiceStore } from "../stores/voiceStore";
import type { WSIncoming } from "../types";

async function speakReply(text: string) {
  const trimmed = text.trim();
  if (!trimmed) return;

  const voiceState = useVoiceStore.getState();
  if (voiceState.isSpeaking) return;

  voiceState.setSpeaking(true);
  let audioContext: AudioContext | null = null;

  try {
    const audioBlob = await postTTS(trimmed);
    audioContext = new AudioContext();
    const buffer = await audioContext.decodeAudioData(await audioBlob.arrayBuffer());
    const source = audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(audioContext.destination);

    await new Promise<void>((resolve) => {
      source.onended = () => resolve();
      source.start();
    });
  } finally {
    voiceState.setSpeaking(false);
    if (audioContext) {
      try {
        await audioContext.close();
      } catch {
        // Ignore close failures; playback has already finished or been interrupted.
      }
    }
  }
}

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
      setGlobalWs(ws);

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
            {
              const messages = useChatStore.getState().messages;
              const lastMessage = messages[messages.length - 1];
              void speakReply(lastMessage?.content ?? "").catch((error) => {
                console.error("[Voice] Failed to play ElevenLabs reply", error);
              });
            }
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
        setGlobalWs(null);
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
      setGlobalWs(null);
    };
  }, []);

  return wsRef;
}
