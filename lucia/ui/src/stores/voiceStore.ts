import { create } from "zustand";

interface VoiceState {
  isRecording: boolean;
  isTranscribing: boolean;
  isSpeaking: boolean;
  transcript: string;

  startRecording: () => void;
  stopRecording: () => void;
  setTranscribing: (v: boolean) => void;
  setSpeaking: (v: boolean) => void;
  setTranscript: (t: string) => void;
  speak: (text: string) => void;
}

export const useVoiceStore = create<VoiceState>((set) => ({
  isRecording: false,
  isTranscribing: false,
  isSpeaking: false,
  transcript: "",

  startRecording: () => set({ isRecording: true }),
  stopRecording: () => set({ isRecording: false }),
  setTranscribing: (v) => set({ isTranscribing: v }),
  setSpeaking: (v) => set({ isSpeaking: v }),
  setTranscript: (t) => set({ transcript: t }),
  speak: () => set({ isSpeaking: true }),
}));
