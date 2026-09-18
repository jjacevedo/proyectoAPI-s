import type { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import styles from './AppShell.module.css';

type SidebarMode = 'normal' | 'evaluation';

type Props = {
  activeView: 'chat' | 'dashboard';
  children: ReactNode;
  mode?: SidebarMode;
  onModeChange?: (mode: SidebarMode) => void;
  activeConversationId?: number | null;
  onSelectConversation?: (id: number) => void;
  onDeleteConversation?: (id: number) => void;
};

export function AppShell({
  activeView,
  children,
  mode,
  onModeChange,
  activeConversationId,
  onSelectConversation,
  onDeleteConversation,
}: Props) {
  return (
    <div className={styles.shell}>
      <div className={styles.center}>
        <div key={`${activeView}-${mode ?? ''}`} className={styles.content}>
          {children}
        </div>
      </div>
      <Sidebar
        activeView={activeView}
        mode={mode}
        onModeChange={onModeChange}
        activeConversationId={activeConversationId}
        onSelectConversation={onSelectConversation}
        onDeleteConversation={onDeleteConversation}
      />
    </div>
  );
}
