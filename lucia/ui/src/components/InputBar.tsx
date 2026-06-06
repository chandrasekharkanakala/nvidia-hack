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
    <div className="shrink-0 border-t border-[var(--color-border)] px-4 py-3">
      {image && (
        <div className="mb-2 flex items-center gap-2">
          <img src={`data:image/png;base64,${image}`} alt="Preview" className="h-12 rounded-lg" />
          <button onClick={() => setImage(undefined)} className="text-xs text-[var(--color-muted)] hover:text-[var(--color-error)]">
            Remove
          </button>
        </div>
      )}
      <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2">
        <AttachButton onAttach={setImage} />
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask about London..."
          rows={1}
          disabled={isStreaming}
          className="flex-1 resize-none bg-transparent text-sm text-[var(--color-text)] placeholder:text-[var(--color-muted)] focus:outline-none disabled:opacity-50"
        />
        <ModeToggle />
        <VoiceButton onTranscript={handleTranscript} />
        <button
          onClick={handleSend}
          disabled={!text.trim() || isStreaming}
          className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-btn)] bg-[var(--color-accent)] text-black transition-opacity disabled:opacity-30"
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
}
