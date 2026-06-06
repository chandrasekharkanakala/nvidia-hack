import type { Message } from "../types";

interface Props {
  message: Message;
}

export function UserMessage({ message }: Props) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] space-y-2">
        {message.image && (
          <img
            src={`data:image/png;base64,${message.image}`}
            alt="Attached"
            className="ml-auto max-h-32 rounded-lg object-cover"
          />
        )}
        <div className="rounded-[var(--radius-card)] bg-[var(--color-surface)] px-4 py-3 text-sm">
          {message.content}
        </div>
      </div>
    </div>
  );
}
