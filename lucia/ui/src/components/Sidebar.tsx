import { Plus } from "lucide-react";
import { useChatStore } from "../stores/chatStore";
import { SessionList } from "./SessionList";

export function Sidebar() {
  const createSession = useChatStore((s) => s.createSession);

  return (
    <aside className="flex w-[260px] shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)]">
      <div className="p-3">
        <button
          onClick={createSession}
          className="flex w-full items-center gap-2 rounded-[var(--radius-btn)] border border-[var(--color-border)] px-3 py-2 text-sm hover:bg-[var(--color-surface-hover)] transition-colors"
        >
          <Plus size={16} />
          New Chat
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-3">
        <SessionList />
      </div>
    </aside>
  );
}
