import { useRef } from "react";
import { Paperclip } from "lucide-react";

interface Props {
  onAttach: (base64: string) => void;
}

export function AttachButton({ onAttach }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const base64 = result.split(",")[1];
      onAttach(base64);
    };
    reader.readAsDataURL(file);

    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <>
      <button
        onClick={() => inputRef.current?.click()}
        className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-btn)] text-[var(--color-muted)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text)]"
        title="Attach image"
      >
        <Paperclip size={16} />
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        onChange={handleChange}
        className="hidden"
      />
    </>
  );
}
