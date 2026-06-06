import { BarChart3, Square, Volume2, VolumeX } from "lucide-react";
import { useChatStore } from "../stores/chatStore";
import { useMetricsStore } from "../stores/metricsStore";
import { useVoiceStore } from "../stores/voiceStore";

export function Header() {
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const sessions = useChatStore((s) => s.sessions);
  const toggle = useMetricsStore((s) => s.toggle);
  const isSpeaking = useVoiceStore((s) => s.isSpeaking);
  const isVoiceEnabled = useVoiceStore((s) => s.isVoiceEnabled);
  const toggleVoiceEnabled = useVoiceStore((s) => s.toggleVoiceEnabled);
  const stopSpeaking = useVoiceStore((s) => s.stopSpeaking);

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
      <div className="flex items-center gap-2">
        <button
          onClick={toggleVoiceEnabled}
          className={`flex items-center gap-1.5 rounded-[var(--radius-btn)] border border-[var(--color-glass-border)] px-3 py-1.5 text-xs backdrop-blur-xl transition-colors ${
            isVoiceEnabled
              ? "bg-[var(--color-glass-surface)] text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]"
              : "bg-[var(--color-glass-surface)] text-[var(--color-muted)] hover:bg-[var(--color-surface-hover)]"
          }`}
          title={isVoiceEnabled ? "Turn voice replies off" : "Turn voice replies on"}
        >
          {isVoiceEnabled ? <Volume2 size={14} /> : <VolumeX size={14} />}
          {isVoiceEnabled ? "Voice On" : "Voice Off"}
        </button>
        {isVoiceEnabled && isSpeaking && (
          <button
            onClick={stopSpeaking}
            className="flex items-center gap-1.5 rounded-[var(--radius-btn)] border border-[var(--color-glass-border)] bg-[var(--color-glass-surface)] px-3 py-1.5 text-xs text-[var(--color-error)] backdrop-blur-xl transition-colors hover:bg-[var(--color-surface-hover)]"
            title="Stop voice playback"
          >
            <Square size={12} />
            Stop Voice
          </button>
        )}
        <button
          onClick={toggle}
          className="flex items-center gap-1.5 rounded-[var(--radius-btn)] border border-[var(--color-glass-border)] bg-[var(--color-glass-surface)] px-3 py-1.5 text-xs text-[var(--color-muted)] backdrop-blur-xl transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text)]"
        >
          <BarChart3 size={14} />
          Metrics
        </button>
      </div>
    </header>
  );
}
