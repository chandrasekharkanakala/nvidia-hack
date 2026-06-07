import { create } from "zustand";

interface VoiceState {
  isRecording: boolean;
  isTranscribing: boolean;
  transcript: string;

  startRecording: () => void;
  stopRecording: () => void;
  setTranscribing: (v: boolean) => void;
  setTranscript: (t: string) => void;
}

export const useVoiceStore = create<VoiceState>((set) => ({
  isRecording: false,
  isTranscribing: false,
  transcript: "",

  startRecording: () => set({ isRecording: true }),
  stopRecording: () => set({ isRecording: false }),
  setTranscribing: (v) => set({ isTranscribing: v }),
  setTranscript: (t) => set({ transcript: t }),
}));
