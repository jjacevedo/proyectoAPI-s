'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { deleteConversation, listConversations } from '@/lib/api';
import { formatRelativeTime } from '@/lib/format';
import type { ConversationSummary } from '@/types/conversation';
import styles from './Sidebar.module.css';

type SidebarMode = 'normal' | 'evaluation';

type Props = {
  activeView: 'chat' | 'dashboard';
  mode?: SidebarMode;
  onModeChange?: (mode: SidebarMode) => void;
  activeConversationId?: number | null;
  onSelectConversation?: (id: number) => void;
  onDeleteConversation?: (id: number) => void;
};

export function Sidebar({
  activeView,
  mode = 'normal',
  onModeChange,
  activeConversationId,
  onSelectConversation,
  onDeleteConversation,
}: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);

  useEffect(() => {
    const mql = window.matchMedia('(max-width: 1024px)');
    setCollapsed(mql.matches);
    const listener = (event: MediaQueryListEvent) => setCollapsed(event.matches);
    mql.addEventListener('change', listener);
    return () => mql.removeEventListener('change', listener);
  }, []);

  useEffect(() => {
    let cancelled = false;
    listConversations()
      .then((res) => {
        if (!cancelled) setConversations(res.conversations);
      })
      .catch(() => {
        if (!cancelled) setConversations([]);
      });
    return () => {
      cancelled = true;
    };
  }, [activeConversationId]);

  async function handleDelete(event: React.MouseEvent, id: number) {
    event.stopPropagation();
    if (!window.confirm('¿Eliminar esta conversación?')) return;
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      onDeleteConversation?.(id);
    } catch {
      // el borrado fallo (backend no disponible, etc.) -- la lista se queda igual.
    }
  }

  if (collapsed) {
    return (
      <button
        type="button"
        className={styles.expandTab}
        onClick={() => setCollapsed(false)}
        aria-label="Mostrar sidebar"
      >
        <ChevronIcon />
      </button>
    );
  }

  return (
    <aside className={styles.sidebar}>
      <button
        type="button"
        className={styles.collapseButton}
        onClick={() => setCollapsed(true)}
        aria-label="Ocultar sidebar"
      >
        <ChevronIcon flipped />
      </button>

      <div className={styles.brand}>
        <div className={styles.brandName}>JJAPIS</div>
        <div className={styles.brandSubtitle}>Multi-LLM Orchestrator</div>
      </div>

      <div className={styles.modeToggle}>
        <div className={styles.modeToggleTrack}>
          <Link
            href="/"
            onClick={() => onModeChange?.('normal')}
            className={`${styles.modeSegment} ${mode === 'normal' && activeView === 'chat' ? styles.modeSegmentActive : ''}`}
          >
            Normal
          </Link>
          <Link
            href="/"
            onClick={() => onModeChange?.('evaluation')}
            className={`${styles.modeSegment} ${mode === 'evaluation' && activeView === 'chat' ? styles.modeSegmentActive : ''}`}
          >
            Evaluación
          </Link>
        </div>
      </div>

      <div className={styles.conversations}>
        {conversations.map((conversation) => (
          <div
            key={conversation.id}
            className={`${styles.conversationItem} ${
              activeConversationId === conversation.id ? styles.conversationItemActive : ''
            }`}
          >
            <button
              type="button"
              className={styles.conversationSelect}
              onClick={() => onSelectConversation?.(conversation.id)}
            >
              <div className={styles.conversationTitle}>{conversation.title}</div>
              <div className={styles.conversationDate}>{formatRelativeTime(conversation.updated_at)}</div>
            </button>
            <button
              type="button"
              className={styles.deleteButton}
              aria-label="Eliminar conversación"
              onClick={(event) => handleDelete(event, conversation.id)}
            >
              <TrashIcon />
            </button>
          </div>
        ))}
      </div>

      <Link
        href="/dashboard"
        className={`${styles.dashboardLink} ${activeView === 'dashboard' ? styles.dashboardLinkActive : ''}`}
      >
        <GridIcon />
        Dashboard de costos
        {activeView === 'dashboard' && <span className={styles.dot} />}
      </Link>
    </aside>
  );
}

function GridIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 6h18" />
      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
    </svg>
  );
}

function ChevronIcon({ flipped }: { flipped?: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      style={{ transform: flipped ? 'rotate(180deg)' : undefined }}
    >
      <path d="M9 18l-6-6 6-6" />
    </svg>
  );
}
