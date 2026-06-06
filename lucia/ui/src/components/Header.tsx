import { BarChart3 } from "lucide-react";
import { useChatStore } from "../stores/chatStore";
import { useMetricsStore } from "../stores/metricsStore";

export function Header() {
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const sessions = useChatStore((s) => s.sessions);
  const toggle = useMetricsStore((s) => s.toggle);

  const session = sessions.find((s) => s.id === activeSessionId);

  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-[var(--color-border)] px-4">
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold text-[var(--color-accent)]">LUCIA</span>
        {session && (
          <span className="text-sm text-[var(--color-muted)] truncate max-w-[300px]">
            {session.title}
          </span>
        )}
      </div>
      <button
        onClick={toggle}
        className="flex items-center gap-1.5 rounded-[var(--radius-btn)] px-2.5 py-1.5 text-xs text-[var(--color-muted)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text)] transition-colors"
      >
        <BarChart3 size={14} />
        Metrics
      </button>
    </header>
  );
}
