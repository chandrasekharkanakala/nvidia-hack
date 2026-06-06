export function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2 text-sm text-[var(--color-muted)]">
      <div className="flex gap-1">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-accent)]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-accent)] [animation-delay:200ms]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-accent)] [animation-delay:400ms]" />
      </div>
      <span>Thinking...</span>
    </div>
  );
}
