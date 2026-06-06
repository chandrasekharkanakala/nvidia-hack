import { Zap, Brain } from "lucide-react";
import { useChatStore } from "../stores/chatStore";

export function ModeToggle() {
  const mode = useChatStore((s) => s.mode);
  const setMode = useChatStore((s) => s.setMode);

  return (
    <div className="flex items-center rounded-full border border-[var(--color-border)] p-0.5">
      <button
        onClick={() => setMode("light")}
        className={`flex items-center gap-1 rounded-full px-2 py-1 text-xs transition-colors ${
          mode === "light"
            ? "bg-[var(--color-accent)] text-black"
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
            ? "bg-[var(--color-accent-deep)] text-white"
            : "text-[var(--color-muted)] hover:text-[var(--color-text)]"
        }`}
        title="Deep mode – thorough analysis"
      >
        <Brain size={12} />
      </button>
    </div>
  );
}
