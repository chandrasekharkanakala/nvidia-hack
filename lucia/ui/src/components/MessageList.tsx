import type { Message } from "../types";
import { UserMessage } from "./UserMessage";
import { AgentMessage } from "./AgentMessage";

interface Props {
  messages: Message[];
}

export function MessageList({ messages }: Props) {
  return (
    <div className="mx-auto max-w-4xl space-y-7">
      {messages.map((msg) =>
        msg.role === "user" ? (
          <UserMessage key={msg.id} message={msg} />
        ) : (
          <AgentMessage key={msg.id} message={msg} />
        )
      )}
    </div>
  );
}
