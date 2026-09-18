import type { ChatResponse } from '@/types/chat';
import { FinalAnswer } from '@/components/FinalAnswer';
import { ModelsParticipated } from '@/components/ModelsParticipated';
import { ExpandableSections } from './ExpandableSections';
import styles from './MessageBubble.module.css';

type Props = {
  role: 'user' | 'assistant';
  content: string;
  response?: ChatResponse;
};

export function MessageBubble({ role, content, response }: Props) {
  if (role === 'user') {
    return (
      <div className={styles.userRow}>
        <div className={styles.userBubble}>{content}</div>
      </div>
    );
  }

  return (
    <div className={styles.assistantMessage}>
      <FinalAnswer answer={content} />
      {response && (
        <>
          <ModelsParticipated
            responses={response.responses}
            latencyMs={response.latency_ms}
            costUsd={response.total_cost_estimated_usd}
          />
          <ExpandableSections response={response} />
        </>
      )}
    </div>
  );
}
