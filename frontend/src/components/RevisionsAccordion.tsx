import type { ProviderResponse } from '@/types/chat';
import styles from './panels.module.css';

export function RevisionsAccordion({ revisions }: { revisions: ProviderResponse[] }) {
  if (revisions.length === 0) return null;

  return (
    <div className={styles.panel}>
      <h3 className={styles.heading}>Reevaluación (respuestas revisadas tras la crítica)</h3>
      {revisions.map((revision, index) => (
        <details key={`${revision.provider}-${revision.model}-${index}`} className={styles.detail}>
          <summary>{revision.provider} / {revision.model}</summary>
          {revision.error ? (
            <p className={styles.error}>{revision.error}</p>
          ) : (
            <div className={styles.response}>{revision.content}</div>
          )}
          <p className={styles.meta}>
            Tokens: {revision.tokens} · Costo: {revision.cost_estimated_usd == null ? 'N/D' : `$${revision.cost_estimated_usd.toFixed(6)}`} · Latencia: {revision.latency_ms.toFixed(0)} ms
          </p>
        </details>
      ))}
    </div>
  );
}
