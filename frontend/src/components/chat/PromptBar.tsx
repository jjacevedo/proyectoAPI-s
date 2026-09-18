'use client';

import type { ConversationMode } from '@/types/chat';
import styles from './PromptBar.module.css';

type Props = {
  prompt: string;
  setPrompt: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
  mode?: ConversationMode;
  onModeChange?: (mode: ConversationMode) => void;
  modeLocked?: boolean;
  submitLabel?: string;
  showModeSelector?: boolean;
  placeholder?: string;
};

const MODE_OPTIONS: { value: ConversationMode; label: string; dotClass: string }[] = [
  { value: 'fast', label: 'Rápido', dotClass: styles.dotSage },
  { value: 'deliberation', label: 'Deliberación', dotClass: styles.dotAmber },
  { value: 'max_verification', label: 'Máx. verificación', dotClass: styles.dotTerracotta },
];

export function PromptBar({
  prompt,
  setPrompt,
  onSubmit,
  loading,
  mode,
  onModeChange,
  modeLocked = false,
  submitLabel = 'Resolver',
  showModeSelector = true,
  placeholder = 'Escribe una tarea para los modelos...',
}: Props) {
  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (!loading && prompt.trim()) onSubmit();
    }
  }

  return (
    <div className={styles.bar}>
      {showModeSelector && (
        <div className={styles.modeRow}>
          {MODE_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              disabled={modeLocked}
              onClick={() => onModeChange?.(option.value)}
              className={`${styles.modePill} ${mode === option.value ? styles.modePillActive : ''}`}
            >
              <span className={`${styles.dot} ${option.dotClass}`} />
              {option.label}
            </button>
          ))}
        </div>
      )}
      <div className={styles.inputRow}>
        <textarea
          className={styles.input}
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          maxLength={12000}
          rows={1}
        />
        <button type="button" className={styles.submit} onClick={onSubmit} disabled={loading || !prompt.trim()}>
          {loading ? 'Consultando...' : submitLabel}
        </button>
      </div>
    </div>
  );
}
