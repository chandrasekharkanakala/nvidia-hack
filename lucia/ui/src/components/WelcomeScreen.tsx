import { useChatStore } from "../stores/chatStore";

const SUGGESTIONS = [
  "What happens to traffic on London Bridge when it rains?",
  "If I close Threadneedle St for 3 weeks, what's the impact?",
  "Show me air quality trends in the City of London",
];

export function WelcomeScreen() {
  const sendMessage = useChatStore((s) => s.sendMessage);

  return (
    <div className="flex flex-col items-center gap-8 px-4 text-center">
      <div>
        <h1 className="text-4xl font-bold text-[var(--color-accent)]">LUCIA</h1>
        <p className="mt-2 text-[var(--color-muted)]">How can I help with London?</p>
      </div>
      <div className="grid w-full max-w-xl gap-3">
        {SUGGESTIONS.map((text) => (
          <button
            key={text}
            onClick={() => sendMessage(text)}
            className="rounded-[var(--radius-card)] border border-[var(--color-border)] p-4 text-left text-sm text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] transition-colors"
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}
