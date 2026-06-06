import { Mic } from "lucide-react";
import { useVoice } from "../hooks/useVoice";
import { useVoiceStore } from "../stores/voiceStore";

interface Props {
  onTranscript: (text: string) => void;
}

export function VoiceButton({ onTranscript }: Props) {
  const { start, stop } = useVoice();
  const isRecording = useVoiceStore((s) => s.isRecording);
  const isTranscribing = useVoiceStore((s) => s.isTranscribing);

  const handlePointerDown = () => {
    start();
  };

  const handlePointerUp = async () => {
    const text = await stop();
    if (text) onTranscript(text);
  };

  return (
    <button
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerUp}
      disabled={isTranscribing}
      className={`relative flex h-8 w-8 items-center justify-center rounded-[var(--radius-btn)] transition-colors ${
        isRecording
          ? "text-[var(--color-error)]"
          : "text-[var(--color-muted)] hover:text-[var(--color-text)]"
      } disabled:opacity-50`}
      title="Hold to record"
    >
      {isRecording && (
        <span className="voice-pulse absolute inset-0 rounded-[var(--radius-btn)] bg-[var(--color-error)]/20" />
      )}
      <Mic size={16} />
    </button>
  );
}
