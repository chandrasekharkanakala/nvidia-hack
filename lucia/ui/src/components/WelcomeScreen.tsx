import { useChatStore } from "../stores/chatStore";
import { CloudRain, Route, Wind, type LucideIcon } from "lucide-react";

const SUGGESTIONS: Array<{
  title: string;
  detail: string;
  prompt: string;
  icon: LucideIcon;
}> = [
  {
    title: "Rain impact",
    detail: "London Bridge traffic shift",
    prompt: "What traffic changes happen on London Bridge during rain?",
    icon: CloudRain,
  },
  {
    title: "Road closure",
    detail: "Threadneedle Street scenario",
    prompt: "If Threadneedle Street closes for three weeks, what is the citywide impact?",
    icon: Route,
  },
  {
    title: "Air quality",
    detail: "City of London trends",
    prompt: "Show air quality trends across the City of London.",
    icon: Wind,
  },
];

export function WelcomeScreen() {
  const sendMessage = useChatStore((s) => s.sendMessage);

  return (
    <div className="flex w-full max-w-4xl flex-col gap-8 px-4">
      <div className="flex items-center gap-4">
        <div className="h-11 w-11 rounded-2xl bg-[var(--color-text)] p-1.5 shadow-[0_6px_18px_rgba(47,36,24,0.22)]">
          <div className="h-full w-full rounded-xl bg-[var(--color-surface)]" />
        </div>
        <div>
          <h1 className="text-3xl font-semibold text-[var(--color-text)]">Start a London intelligence chat</h1>
        </div>
      </div>
      <div className="grid w-full gap-3 md:grid-cols-3">
        {SUGGESTIONS.map(({ title, detail, prompt, icon: Icon }) => (
          <button
            key={title}
            onClick={() => sendMessage(prompt)}
            className="group rounded-2xl border border-[var(--color-glass-border)] bg-[var(--color-glass-surface)] p-4 text-left backdrop-blur-xl transition-all hover:-translate-y-0.5 hover:border-[var(--color-accent)]/45 hover:bg-[var(--color-surface-hover)]"
          >
            <div className="mb-3 inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--color-surface-hover)] text-[var(--color-accent)] transition-colors group-hover:bg-[var(--color-text)] group-hover:text-white">
              <Icon size={16} />
            </div>
            <p className="text-sm font-semibold text-[var(--color-text)]">{title}</p>
            <p className="mt-1 text-xs text-[var(--color-muted)]">{detail}</p>
          </button>
        ))}
      </div>
      <p className="text-xs text-[var(--color-muted)]">
        Or type your own question below.
      </p>
    </div>
  );
}
