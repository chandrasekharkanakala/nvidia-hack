import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
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
    <div className="flex justify-start">
      <div className="max-w-[80%] space-y-2">
        {isThinking && !showToolCall && <ThinkingIndicator />}
        {showToolCall && (
          <ToolCallIndicator tool={currentToolCall.tool} description={currentToolCall.description} />
        )}
        {message.content && (
          <div
            className={`prose prose-invert prose-sm max-w-none text-sm leading-relaxed ${
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
