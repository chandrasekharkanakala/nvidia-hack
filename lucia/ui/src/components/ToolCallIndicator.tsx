import { Cog } from "lucide-react";

interface Props {
  tool: string;
  description: string;
}

const TOOL_LABELS: Record<string, string> = {
  rag_search: "Searching documents...",
  sql_query: "Querying data...",
  web_search: "Searching the web...",
  code_interpreter: "Running code...",
  simulation: "Running simulation...",
};

export function ToolCallIndicator({ tool, description }: Props) {
  const label = description || TOOL_LABELS[tool] || `Using ${tool}...`;

  return (
    <div className="flex items-center gap-2 rounded-[var(--radius-btn)] bg-[var(--color-surface)] px-3 py-2 text-xs text-[var(--color-muted)]">
      <Cog size={14} className="tool-spin text-[var(--color-accent)]" />
      <span>{label}</span>
    </div>
  );
}
