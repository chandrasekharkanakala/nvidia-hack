import { useChatStore } from "../stores/chatStore";
import { WelcomeScreen } from "./WelcomeScreen";
import { MessageList } from "./MessageList";
import { useAutoScroll } from "../hooks/useAutoScroll";

export function MessageArea() {
  const messages = useChatStore((s) => s.messages);
  const { containerRef, handleScroll } = useAutoScroll([messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center overflow-hidden">
        <WelcomeScreen />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-4 py-6"
    >
      <MessageList messages={messages} />
    </div>
  );
}
