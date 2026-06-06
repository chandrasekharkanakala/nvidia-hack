import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot } from "lucide-react";
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
        {message.content && (
          <div
            className={`prose prose-sm max-w-none rounded-2xl border border-[var(--color-glass-border)] bg-[var(--color-glass-surface)] px-4 py-3 text-sm leading-relaxed shadow-[0_2px_8px_rgba(47,36,24,0.06)] backdrop-blur-xl ${
              isLast && isStreaming ? "streaming-cursor" : ""
            }`}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
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
