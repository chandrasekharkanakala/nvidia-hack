import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, BarChart3 } from "lucide-react";
import type { Message } from "../types";
import { useChatStore } from "../stores/chatStore";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { ToolCallIndicator } from "./ToolCallIndicator";

interface Props {
  message: Message;
}

export function AgentMessage({ message }: Props) {
  const isStreaming = useChatStore((s) => s.isStreaming);
  const currentToolCall = useChatStore((s) => s.currentToolCall);
  const messages = useChatStore((s) => s.messages);
  const isLast = messages[messages.length - 1]?.id === message.id;
  const isThinking = isLast && isStreaming && !message.content;
  const showToolCall = isLast && currentToolCall;

  return (
    <div className="message-in flex items-start gap-3">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-muted)]">
        <Bot size={14} />
      </div>
      <div className="min-w-0 max-w-[85%] space-y-2">
        {isThinking && !showToolCall && <ThinkingIndicator />}
        {showToolCall && (
          <ToolCallIndicator tool={currentToolCall.tool} description={currentToolCall.description} />
        )}
        {message.chart && (
          <div className="rounded-2xl border border-[var(--color-glass-border)] bg-[var(--color-glass-surface)] p-3 shadow-[0_2px_8px_rgba(47,36,24,0.06)] backdrop-blur-xl">
            <div className="mb-2 flex items-center gap-2 text-xs text-[var(--color-muted)]">
              <BarChart3 size={12} />
              <span>Generated Visualization</span>
            </div>
            <img
              src={`data:image/png;base64,${message.chart}`}
              alt="Data visualization"
              className="w-full rounded-lg"
            />
          </div>
        )}
        {message.content && (
          <div
            className={`prose prose-sm max-w-none rounded-2xl border border-[var(--color-glass-border)] bg-[var(--color-glass-surface)] px-4 py-3 text-sm leading-relaxed shadow-[0_2px_8px_rgba(47,36,24,0.06)] backdrop-blur-xl ${
              isLast && isStreaming ? "streaming-cursor" : ""
            }`}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        )}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.toolCalls.map((tc, i) => (
              <span
                key={i}
                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${
                  tc.success
                    ? "bg-green-500/10 text-green-400"
                    : "bg-red-500/10 text-red-400"
                }`}
              >
                {tc.tool}
                <span className="text-[10px] opacity-60">{tc.durationMs}ms</span>
              </span>
            ))}
          </div>
        )}
        {message.metrics && (
          <div className="flex items-center gap-2 text-xs text-[var(--color-muted)]">
            <span>{message.metrics.latencyMs}ms</span>
            <span>·</span>
            <span>{message.metrics.tokensCompletion} tokens</span>
          </div>
        )}
      </div>
    </div>
  );
}
