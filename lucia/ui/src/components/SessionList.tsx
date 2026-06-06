import { MessageSquare } from "lucide-react";
import { useChatStore } from "../stores/chatStore";
import type { Session } from "../types";

function groupByDate(sessions: Session[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterday = today - 86400000;

  const groups: { label: string; sessions: Session[] }[] = [
    { label: "Today", sessions: [] },
    { label: "Yesterday", sessions: [] },
    { label: "Older", sessions: [] },
  ];

  for (const s of sessions) {
    const t = new Date(s.lastActivity).getTime();
    if (t >= today) groups[0].sessions.push(s);
    else if (t >= yesterday) groups[1].sessions.push(s);
    else groups[2].sessions.push(s);
  }

  return groups.filter((g) => g.sessions.length > 0);
}

export function SessionList() {
  const sessions = useChatStore((s) => s.sessions);
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const loadSession = useChatStore((s) => s.loadSession);
  const groups = groupByDate(sessions);

  return (
    <div className="space-y-4">
      {groups.map((group) => (
        <div key={group.label}>
          <p className="px-2 pb-1 text-xs font-medium text-[var(--color-muted)]">
            {group.label}
          </p>
          <div className="space-y-0.5">
            {group.sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => loadSession(session.id)}
                className={`flex w-full items-center gap-2 rounded-[var(--radius-btn)] px-2 py-1.5 text-left text-sm transition-colors ${
                  session.id === activeSessionId
                    ? "bg-[var(--color-surface-hover)] text-[var(--color-text)]"
                    : "text-[var(--color-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text)]"
                }`}
              >
                <MessageSquare size={14} className="shrink-0" />
                <span className="truncate">{session.title}</span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
