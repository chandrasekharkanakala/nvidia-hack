import { X, Clock, Hash, Wrench } from "lucide-react";
import { useMetricsStore } from "../stores/metricsStore";
import { useChatStore } from "../stores/chatStore";

export function MetricsPanel() {
  const isOpen = useMetricsStore((s) => s.isOpen);
  const toggle = useMetricsStore((s) => s.toggle);
  const latency = useMetricsStore((s) => s.latency);
  const tokens = useMetricsStore((s) => s.tokens);
  const toolCalls = useMetricsStore((s) => s.toolCalls);
  const messages = useChatStore((s) => s.messages);

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant" && m.metrics);

  if (!isOpen) return null;

  return (
    <div className="absolute right-0 top-0 z-50 flex h-full w-80 flex-col border-l border-[var(--color-border)] bg-[var(--color-bg)]">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
        <span className="text-sm font-medium">Metrics</span>
        <button
          onClick={toggle}
          className="text-[var(--color-muted)] hover:text-[var(--color-text)]"
        >
          <X size={16} />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <MetricCard
          icon={<Clock size={14} />}
          label="Latency"
          value={
            lastAssistant?.metrics
              ? `${lastAssistant.metrics.timeToFirstTokenMs}ms TTFT / ${lastAssistant.metrics.latencyMs}ms total`
              : `${latency}ms`
          }
        />
        <MetricCard
          icon={<Hash size={14} />}
          label="Tokens"
          value={
            lastAssistant?.metrics
              ? `${lastAssistant.metrics.tokensPrompt} prompt + ${lastAssistant.metrics.tokensCompletion} completion`
              : `${tokens} completion`
          }
        />
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs text-[var(--color-muted)]">
            <Wrench size={14} />
            <span>Tool Calls</span>
          </div>
          {(lastAssistant?.toolCalls || toolCalls).length === 0 ? (
            <p className="text-xs text-[var(--color-muted)]">No tool calls yet</p>
          ) : (
            <div className="space-y-1">
              {(lastAssistant?.toolCalls || toolCalls).map((tc, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-[var(--radius-btn)] bg-[var(--color-surface)] px-3 py-1.5 text-xs"
                >
                  <span className="text-[var(--color-text)]">{tc.tool}</span>
                  <span className={tc.success ? "text-[var(--color-accent)]" : "text-[var(--color-error)]"}>
                    {tc.durationMs}ms
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius-card)] bg-[var(--color-surface)] p-3">
      <div className="mb-1 flex items-center gap-2 text-xs text-[var(--color-muted)]">
        {icon}
        <span>{label}</span>
      </div>
      <p className="text-sm font-medium text-[var(--color-text)]">{value}</p>
    </div>
  );
}
