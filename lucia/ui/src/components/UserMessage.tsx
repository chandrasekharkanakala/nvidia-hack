import { User } from "lucide-react";
import type { Message } from "../types";

interface Props {
  message: Message;
}

export function UserMessage({ message }: Props) {
  return (
    <div className="message-in flex justify-end">
      <div className="flex max-w-[85%] items-start gap-3">
        <div className="min-w-0 space-y-2">
          {message.image && (
            <img
              src={`data:image/png;base64,${message.image}`}
              alt="Attached"
              className="ml-auto max-h-32 rounded-xl border border-[var(--color-border)] object-cover"
            />
          )}
          <div className="rounded-2xl bg-[var(--color-text)] px-4 py-3 text-sm text-white shadow-[0_2px_8px_rgba(47,36,24,0.12)]">
            {message.content}
          </div>
        </div>
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-muted)]">
          <User size={14} />
        </div>
      </div>
    </div>
  );
}
