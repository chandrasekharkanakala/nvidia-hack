import { useState, useRef, useCallback, type KeyboardEvent } from "react";
import { Send } from "lucide-react";
import { useChatStore } from "../stores/chatStore";
import { ModeToggle } from "./ModeToggle";
import { VoiceButton } from "./VoiceButton";
import { AttachButton } from "./AttachButton";

export function InputBar() {
  const [text, setText] = useState("");
  const [image, setImage] = useState<string | undefined>();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const isStreaming = useChatStore((s) => s.isStreaming);

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;
    sendMessage(trimmed, image);
    setText("");
    setImage(undefined);
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }, [text, image, isStreaming, sendMessage]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  };

  const handleTranscript = (transcript: string) => {
    setText((prev) => prev + transcript);
  };

  return (
    <div className="shrink-0 border-t border-[var(--color-glass-border)] bg-[var(--color-glass-surface)] px-4 py-4 backdrop-blur-xl">
      {image && (
        <div className="mx-auto mb-3 flex max-w-4xl items-center gap-2 rounded-xl border border-[var(--color-glass-border)] bg-[var(--color-glass-surface)] p-2 backdrop-blur-xl">
          <img
            src={`data:image/png;base64,${image}`}
            alt="Preview"
            className="h-12 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]"
          />
          <button
            onClick={() => setImage(undefined)}
            className="text-xs text-[var(--color-muted)] hover:text-[var(--color-error)]"
          >
            Remove
          </button>
        </div>
      )}
      <div className="mx-auto flex max-w-4xl items-center gap-2 rounded-2xl border border-[var(--color-glass-border)] bg-[var(--color-glass-surface)] px-3 py-2.5 shadow-[var(--shadow-glass)] backdrop-blur-xl">
        <AttachButton onAttach={setImage} />
        <div className="flex min-h-9 flex-1 items-center">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Message LUCIA Prime..."
            rows={1}
            disabled={isStreaming}
            className="w-full resize-none bg-transparent py-0 text-sm leading-5 text-[var(--color-text)] placeholder:text-[var(--color-muted)] focus:outline-none disabled:opacity-50"
          />
        </div>
        <ModeToggle />
        <VoiceButton onTranscript={handleTranscript} />
        <button
          onClick={handleSend}
          disabled={!text.trim() || isStreaming}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--color-text)] text-white shadow-[0_2px_8px_rgba(47,36,24,0.25)] transition-opacity hover:opacity-90 disabled:opacity-30 disabled:shadow-none"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
