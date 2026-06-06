import { create } from "zustand";
import type { ToolCallEvent } from "../types";

interface MetricsState {
  isOpen: boolean;
  latency: number;
  tokens: number;
  toolCalls: ToolCallEvent[];

  toggle: () => void;
  update: (data: { latency?: number; tokens?: number; toolCalls?: ToolCallEvent[] }) => void;
  reset: () => void;
}

export const useMetricsStore = create<MetricsState>((set) => ({
  isOpen: false,
  latency: 0,
  tokens: 0,
  toolCalls: [],

  toggle: () => set((s) => ({ isOpen: !s.isOpen })),
  update: (data) => set((s) => ({ ...s, ...data })),
  reset: () => set({ latency: 0, tokens: 0, toolCalls: [] }),
}));
