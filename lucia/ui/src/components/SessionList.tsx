import { MessageSquare } from "lucide-react";
import { useChatStore } from "../stores/chatStore";
import type { Session } from "../types";

type ActivityFilter = "all" | "today" | "week";

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

function formatLastActivity(iso: string) {
  const now = Date.now();
  const ms = now - new Date(iso).getTime();
  const minute = 60000;
  const hour = 3600000;
  const day = 86400000;

  if (ms < minute) return "Just now";
  if (ms < hour) return `${Math.floor(ms / minute)}m ago`;
  if (ms < day) return `${Math.floor(ms / hour)}h ago`;
  return `${Math.floor(ms / day)}d ago`;
}

interface Props {
  searchQuery?: string;
  activityFilter?: ActivityFilter;
}

export function SessionList({ searchQuery = "", activityFilter = "all" }: Props) {
  const sessions = useChatStore((s) => s.sessions);
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const loadSession = useChatStore((s) => s.loadSession);
  const now = Date.now();
  const dayMs = 86400000;
  const normalizedQuery = searchQuery.trim().toLowerCase();

  const filteredSessions = sessions.filter((session) => {
    const titleMatch =
      normalizedQuery.length === 0 || session.title.toLowerCase().includes(normalizedQuery);
    if (!titleMatch) return false;

    const activityMs = new Date(session.lastActivity).getTime();
    if (activityFilter === "today") return activityMs >= now - dayMs;
    if (activityFilter === "week") return activityMs >= now - dayMs * 7;
    return true;
  });

  const groups = groupByDate(filteredSessions);

  if (groups.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)]/70 p-4 text-xs text-[var(--color-muted)]">
        No matching conversations found.
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {groups.map((group) => (
        <div key={group.label}>
          <p className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-muted)]/80">
            {group.label}
          </p>
          <div className="space-y-1">
            {group.sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => loadSession(session.id)}
                className={`group relative flex w-full items-center gap-2 rounded-[var(--radius-btn)] border px-2.5 py-2 text-left text-sm transition-colors ${
                  session.id === activeSessionId
                    ? "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] shadow-[0_1px_4px_rgba(47,36,24,0.08)]"
                    : "border-transparent text-[var(--color-muted)] hover:border-[var(--color-border)] hover:bg-[var(--color-surface)] hover:text-[var(--color-text)]"
                }`}
              >
                {session.id === activeSessionId && (
                  <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-r bg-[var(--color-accent)]" />
                )}
                <MessageSquare
                  size={14}
                  className={`shrink-0 ${session.id === activeSessionId ? "text-[var(--color-accent)]" : "group-hover:text-[var(--color-accent)]"}`}
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate">{session.title}</p>
                  <p className="mt-0.5 text-[11px] text-[var(--color-muted)]">
                    {session.messageCount} msgs · {formatLastActivity(session.lastActivity)}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
