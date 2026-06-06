import { create } from "zustand";

interface VoiceState {
  isRecording: boolean;
  isTranscribing: boolean;
  isSpeaking: boolean;
  isVoiceEnabled: boolean;
  transcript: string;
  stopSpeakingHandler: (() => void) | null;

  startRecording: () => void;
  stopRecording: () => void;
  setTranscribing: (v: boolean) => void;
  setSpeaking: (v: boolean) => void;
  setVoiceEnabled: (v: boolean) => void;
  toggleVoiceEnabled: () => void;
  setStopSpeakingHandler: (handler: (() => void) | null) => void;
  stopSpeaking: () => void;
  setTranscript: (t: string) => void;
  speak: (text: string) => void;
}

export const useVoiceStore = create<VoiceState>((set) => ({
  isRecording: false,
  isTranscribing: false,
  isSpeaking: false,
  isVoiceEnabled: false,
  transcript: "",
  stopSpeakingHandler: null,

  startRecording: () => set({ isRecording: true }),
  stopRecording: () => set({ isRecording: false }),
  setTranscribing: (v) => set({ isTranscribing: v }),
  setSpeaking: (v) => set({ isSpeaking: v }),
  setVoiceEnabled: (v) =>
    set((state) => {
      if (!v) state.stopSpeakingHandler?.();
      return {
        isVoiceEnabled: v,
        isSpeaking: v ? state.isSpeaking : false,
        stopSpeakingHandler: v ? state.stopSpeakingHandler : null,
      };
    }),
  toggleVoiceEnabled: () =>
    set((state) => {
      const next = !state.isVoiceEnabled;
      if (!next) state.stopSpeakingHandler?.();
      return {
        isVoiceEnabled: next,
        isSpeaking: next ? state.isSpeaking : false,
        stopSpeakingHandler: next ? state.stopSpeakingHandler : null,
      };
    }),
  setStopSpeakingHandler: (handler) => set({ stopSpeakingHandler: handler }),
  stopSpeaking: () =>
    set((state) => {
      state.stopSpeakingHandler?.();
      return { isSpeaking: false, stopSpeakingHandler: null };
    }),
  setTranscript: (t) => set({ transcript: t }),
  speak: () => set({ isSpeaking: true }),
}));
