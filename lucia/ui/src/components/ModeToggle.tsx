import { Zap, Brain } from "lucide-react";
import { useChatStore } from "../stores/chatStore";

export function ModeToggle() {
  const mode = useChatStore((s) => s.mode);
  const setMode = useChatStore((s) => s.setMode);

  return (
    <div className="flex items-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)]/80 p-0.5">
      <button
        onClick={() => setMode("light")}
        className={`flex items-center gap-1 rounded-full px-2 py-1 text-xs transition-colors ${
          mode === "light"
            ? "bg-[var(--color-accent)] text-white shadow-[0_4px_14px_rgba(138,106,68,0.35)]"
            : "text-[var(--color-muted)] hover:text-[var(--color-text)]"
        }`}
        title="Light mode – fast responses"
      >
        <Zap size={12} />
      </button>
      <button
        onClick={() => setMode("deep")}
        className={`flex items-center gap-1 rounded-full px-2 py-1 text-xs transition-colors ${
          mode === "deep"
            ? "bg-[var(--color-accent-deep)] text-white shadow-[0_4px_14px_rgba(139,92,246,0.35)]"
            : "text-[var(--color-muted)] hover:text-[var(--color-text)]"
        }`}
        title="Deep mode – thorough analysis"
      >
        <Brain size={12} />
      </button>
    </div>
  );
}
