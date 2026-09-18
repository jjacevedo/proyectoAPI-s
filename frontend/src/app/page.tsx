'use client';

import { useEffect, useState } from 'react';
import { AppShell } from '@/components/shell/AppShell';
import { ChatView } from '@/components/chat/ChatView';
import { EvaluationView } from '@/components/evaluation/EvaluationView';

type SidebarMode = 'normal' | 'evaluation';

const SIDEBAR_MODE_KEY = 'jjapis:sidebarMode';

export default function Home() {
  const [sidebarMode, setSidebarModeState] = useState<SidebarMode>('normal');
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [resumeConversationId, setResumeConversationId] = useState<number | null>(null);

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(SIDEBAR_MODE_KEY);
      if (stored === 'normal' || stored === 'evaluation') setSidebarModeState(stored);
    } catch {
      // sessionStorage inaccesible (modo privado, etc.) — se queda en el modo por defecto.
    }
  }, []);

  function setSidebarMode(next: SidebarMode) {
    setSidebarModeState(next);
    try {
      sessionStorage.setItem(SIDEBAR_MODE_KEY, next);
    } catch {
      // no persiste entre rutas, pero no rompe la interacción actual.
    }
  }

  function handleSelectConversation(id: number) {
    setSidebarMode('normal');
    setActiveConversationId(id);
    setResumeConversationId(id);
  }

  return (
    <AppShell
      activeView="chat"
      mode={sidebarMode}
      onModeChange={setSidebarMode}
      activeConversationId={activeConversationId}
      onSelectConversation={handleSelectConversation}
    >
      {sidebarMode === 'normal' ? (
        <ChatView onConversationIdChange={setActiveConversationId} resumeConversationId={resumeConversationId} />
      ) : (
        <EvaluationView />
      )}
    </AppShell>
  );
}
