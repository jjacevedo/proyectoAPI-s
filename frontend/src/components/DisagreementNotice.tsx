import type { ChatResponse } from '@/types/chat';
import styles from './panels.module.css';

type Props = Pick<ChatResponse, 'disagreement_level' | 'disagreement_reason' | 'disagreement_evidence'>;

export function DisagreementNotice({ disagreement_level, disagreement_reason, disagreement_evidence }: Props) {
  if (disagreement_level === 'not_applicable') return null;

  return (
    <div className={styles.panel}>
      <h3 className={styles.heading}>Desacuerdo entre modelos</h3>
      <p className={disagreement_level === 'disagreement' ? styles.error : styles.meta}>
        {disagreement_level}: {disagreement_reason}
      </p>
      {disagreement_evidence.length > 0 && (
        <ul className={styles.list}>
          {disagreement_evidence.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
