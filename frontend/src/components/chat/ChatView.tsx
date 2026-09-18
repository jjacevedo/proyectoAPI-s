'use client';

import { useEffect, useRef, useState } from 'react';
import { getConversationMessages, sendChat } from '@/lib/api';
import { deriveTitle } from '@/lib/format';
import type { ChatResponse, ConversationMode } from '@/types/chat';
import { MessageBubble } from './MessageBubble';
import { PromptBar } from './PromptBar';
import styles from './ChatView.module.css';

type Turn = { role: 'user' | 'assistant'; content: string; response?: ChatResponse };

const MODE_LABELS: Record<ConversationMode, string> = {
  fast: 'Rápido',
  deliberation: 'Deliberación',
  max_verification: 'Máx. verificación',
};

type Props = {
  onConversationIdChange?: (id: number | null) => void;
  resumeConversationId?: number | null;
};

export function ChatView({ onConversationIdChange, resumeConversationId }: Props) {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<ConversationMode>('deliberation');
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [restored, setRestored] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const messagesRef = useRef<HTMLDivElement>(null);
  const lastResumeId = useRef<number | null | undefined>(undefined);

  useEffect(() => {
    if (resumeConversationId == null) return;
    if (resumeConversationId === lastResumeId.current) return;
    lastResumeId.current = resumeConversationId;
    setConversationId(resumeConversationId);
    setError(null);
    setTurns([]);
    setRestored(false);
    setRestoring(true);
    getConversationMessages(resumeConversationId)
      .then((res) => {
        // Los turnos restaurados solo traen texto (role+content): request_logs no
        // guarda conversation_id, asi que no hay forma de recuperar las respuestas
        // por proveedor/criticas/verificacion de turnos pasados -- no se fabrica un
        // ChatResponse falso, MessageBubble ya maneja `response` ausente sin acordeones.
        setTurns(res.messages.map((m) => ({ role: m.role, content: m.content })));
        setRestored(true);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo cargar la conversación'))
      .finally(() => setRestoring(false));
  }, [resumeConversationId]);

  useEffect(() => {
    messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: 'smooth' });
  }, [turns]);

  async function handleSubmit() {
    const promptSnapshot = prompt;
    if (!promptSnapshot.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await sendChat(promptSnapshot, { conversationId, mode });
      setTurns((prev) => [
        ...prev,
        { role: 'user', content: promptSnapshot },
        { role: 'assistant', content: result.final_answer, response: result },
      ]);
      setConversationId(result.conversation_id);
      setRestored(false);
      onConversationIdChange?.(result.conversation_id);
      setPrompt('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  }

  const latestResponse = [...turns].reverse().find((t) => t.response)?.response;
  const title = turns.length > 0 ? deriveTitle(turns[0].content, 60) : 'Nueva conversación';
  const subtitle = latestResponse
    ? `${MODE_LABELS[mode]} · ${latestResponse.models_used.length} modelos · ${latestResponse.total_tokens} tokens`
    : restored
      ? `Conversación restaurada · ${turns.length} mensajes`
      : 'Escribe tu primera tarea para empezar';

  return (
    <>
      <div className={styles.header}>
        <div>
          <div className={styles.title}>{title}</div>
          <div className={styles.subtitle}>{subtitle}</div>
        </div>
        {conversationId != null && <div className={styles.convId}>Conv #{conversationId}</div>}
      </div>

      <div className={styles.messages} ref={messagesRef}>
        {restoring && <div className={styles.subtitle}>Cargando conversación...</div>}
        {turns.map((turn, index) => (
          <MessageBubble key={index} role={turn.role} content={turn.content} response={turn.response} />
        ))}
        {error && <div className={styles.error}>{error}</div>}
      </div>

      <PromptBar
        prompt={prompt}
        setPrompt={setPrompt}
        onSubmit={handleSubmit}
        loading={loading}
        mode={mode}
        onModeChange={setMode}
        modeLocked={conversationId !== null}
      />
    </>
  );
}
