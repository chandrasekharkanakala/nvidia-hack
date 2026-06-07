import { useRef, useCallback } from "react";
import { useVoiceStore } from "../stores/voiceStore";
import { postSTT } from "../lib/api";

export function useVoice() {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const { startRecording, stopRecording, setTranscribing, setTranscript } = useVoiceStore();

  const start = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
    mediaRecorderRef.current = recorder;
    chunksRef.current = [];

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.start();
    startRecording();
  }, [startRecording]);

  const stop = useCallback(async (): Promise<string> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder) {
        resolve("");
        return;
      }

      recorder.onstop = async () => {
        stopRecording();
        setTranscribing(true);

        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        try {
          const text = await postSTT(blob);
          setTranscript(text);
          resolve(text);
        } catch {
          resolve("");
        } finally {
          setTranscribing(false);
          recorder.stream.getTracks().forEach((t) => t.stop());
        }
      };

      recorder.stop();
    });
  }, [stopRecording, setTranscribing, setTranscript]);
  return { start, stop };
}
