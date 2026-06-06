import { useRef, useCallback } from "react";
import { useVoiceStore } from "../stores/voiceStore";
import { postSTT, postTTS } from "../lib/api";

export function useVoice() {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const { startRecording, stopRecording, setTranscribing, setSpeaking, setTranscript } =
    useVoiceStore();

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

  const speak = useCallback(async (text: string) => {
    setSpeaking(true);
    try {
      const audioBlob = await postTTS(text);
      const ctx = new AudioContext();
      const buffer = await ctx.decodeAudioData(await audioBlob.arrayBuffer());
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);
      source.onended = () => setSpeaking(false);
      source.start();
    } catch {
      setSpeaking(false);
    }
  }, [setSpeaking]);

  return { start, stop, speak };
}
