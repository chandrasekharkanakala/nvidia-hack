import { useMemo, useState } from "react";
import { Plus, Search } from "lucide-react";
import { useChatStore } from "../stores/chatStore";
import { SessionList } from "./SessionList";

type ActivityFilter = "all" | "today" | "week";
const TECH_LOGOS = [
  { name: "NVIDIA", src: new URL("../assets/logos/nvidia.svg", import.meta.url).href },
  { name: "IIElemevenlabs", src: new URL("../assets/logos/elevenlabs.svg", import.meta.url).href },
  { name: "Nebius", src: new URL("../assets/logos/nebius.svg", import.meta.url).href },
  { name: "HP", src: new URL("../assets/logos/hp.svg", import.meta.url).href },
];

export function Sidebar() {
  const createSession = useChatStore((s) => s.createSession);
  const sessions = useChatStore((s) => s.sessions);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<ActivityFilter>("all");

  const filteredCount = useMemo(() => {
    const now = Date.now();
    const dayMs = 86400000;
    const normalizedQuery = query.trim().toLowerCase();

    return sessions.filter((session) => {
      const titleMatch =
        normalizedQuery.length === 0 || session.title.toLowerCase().includes(normalizedQuery);
      if (!titleMatch) return false;

      const activityMs = new Date(session.lastActivity).getTime();
      if (filter === "today") return activityMs >= now - dayMs;
      if (filter === "week") return activityMs >= now - dayMs * 7;
      return true;
    }).length;
  }, [sessions, query, filter]);

  return (
    <aside className="flex w-[300px] shrink-0 flex-col border-r border-[var(--color-border)] bg-[#f1e6d5]">
      <div className="border-b border-[var(--color-border)] bg-[linear-gradient(180deg,#f5ead9_0%,#f1e6d5_100%)] px-4 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--color-muted)]">
          LUCIA PRIME
        </p>
        <p className="mt-1 text-xs text-[var(--color-muted)]">London Command Center</p>
      </div>
      <div className="p-4">
        <button
          onClick={createSession}
          className="flex w-full items-center justify-center gap-2 rounded-[var(--radius-btn)] bg-[var(--color-text)] px-3 py-2.5 text-sm font-medium text-white shadow-[0_4px_12px_rgba(47,36,24,0.2)] transition-opacity hover:opacity-90"
        >
          <Plus size={16} />
          New Chat
        </button>
      </div>
      <div className="space-y-3 px-4 pb-2">
        <label className="flex items-center gap-2 rounded-[var(--radius-btn)] border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-2">
          <Search size={14} className="text-[var(--color-muted)]" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search chats"
            className="w-full bg-transparent text-xs text-[var(--color-text)] placeholder:text-[var(--color-muted)] focus:outline-none"
          />
        </label>
        <div className="flex gap-1">
          {(["all", "today", "week"] as const).map((option) => (
            <button
              key={option}
              onClick={() => setFilter(option)}
              className={`rounded-full px-2.5 py-1 text-[11px] font-medium capitalize transition-colors ${
                filter === option
                  ? "bg-[var(--color-text)] text-white"
                  : "bg-[var(--color-surface)] text-[var(--color-muted)] hover:text-[var(--color-text)]"
              }`}
            >
              {option}
            </button>
          ))}
        </div>
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[var(--color-muted)]/90">
            Recent chats
          </p>
          <span className="rounded-full bg-[var(--color-surface)] px-2 py-0.5 text-[11px] font-medium text-[var(--color-muted)]">
            {filteredCount}
          </span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-3 pb-4">
        <SessionList searchQuery={query} activityFilter={filter} />
      </div>
      <div className="shrink-0 border-t border-[var(--color-border)] px-3 py-3">
        <p className="px-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--color-muted)]/80">
          Powered by
        </p>
        <div className="mt-2 overflow-hidden">
          <div className="tech-roll flex w-max items-center gap-2">
            {[...TECH_LOGOS, ...TECH_LOGOS].map((logo, index) => (
              <div
                key={`${logo.name}-${index}`}
                title={logo.name}
                aria-label={logo.name}
                className="flex h-7 min-w-14 items-center justify-center rounded-md border border-[var(--color-border)] bg-[#ecdfcc] px-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.35)]"
              >
                <img
                  src={logo.src}
                  alt={logo.name}
                  className="h-4 w-auto object-contain mix-blend-multiply opacity-90"
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
