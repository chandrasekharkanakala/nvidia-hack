import { useChatStore } from "../stores/chatStore";
import { WelcomeScreen } from "./WelcomeScreen";
import { MessageList } from "./MessageList";
import { useAutoScroll } from "../hooks/useAutoScroll";

export function MessageArea() {
  const messages = useChatStore((s) => s.messages);
  const { containerRef, handleScroll } = useAutoScroll([messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 justify-center overflow-y-auto px-6 pb-8 pt-14">
        <WelcomeScreen />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-6 py-8"
    >
      <MessageList messages={messages} />
    </div>
  );
}
