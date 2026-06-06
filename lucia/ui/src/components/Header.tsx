import { BarChart3 } from "lucide-react";
import { useChatStore } from "../stores/chatStore";
import { useMetricsStore } from "../stores/metricsStore";

export function Header() {
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const sessions = useChatStore((s) => s.sessions);
  const toggle = useMetricsStore((s) => s.toggle);

  const session = sessions.find((s) => s.id === activeSessionId);

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--color-glass-border)] bg-[var(--color-glass-surface)] px-6 backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <span className="rounded-full border border-[var(--color-glass-border)] bg-[var(--color-surface-hover)]/85 px-2.5 py-1 text-xs font-semibold text-[var(--color-muted)]">
          LUCIA
        </span>
        <span className="text-sm font-semibold text-[var(--color-text)]">
          {session?.title || "New conversation"}
        </span>
      </div>
      <button
        onClick={toggle}
        className="flex items-center gap-1.5 rounded-[var(--radius-btn)] border border-[var(--color-glass-border)] bg-[var(--color-glass-surface)] px-3 py-1.5 text-xs text-[var(--color-muted)] backdrop-blur-xl transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text)]"
      >
        <BarChart3 size={14} />
        Metrics
      </button>
    </header>
  );
}
