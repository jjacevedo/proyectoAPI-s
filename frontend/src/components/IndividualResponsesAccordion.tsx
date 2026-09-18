import type { ProviderResponse } from '@/types/chat';
import styles from './panels.module.css';

export function IndividualResponsesAccordion({ responses }: { responses: ProviderResponse[] }) {
  return (
    <div className={styles.panel}>
      <h3 className={styles.heading}>Respuestas individuales</h3>
      {responses.map((response, index) => (
        <details key={`${response.provider}-${response.model}-${index}`} className={styles.detail}>
          <summary>{response.provider} / {response.model}</summary>
          {response.error ? (
            <p className={styles.error}>{response.error}</p>
          ) : (
            <div className={styles.response}>{response.content}</div>
          )}
          <p className={styles.meta}>
            Tokens: {response.tokens} · Costo: {response.cost_estimated_usd == null ? 'N/D' : `$${response.cost_estimated_usd.toFixed(6)}`} · Latencia: {response.latency_ms.toFixed(0)} ms
          </p>
        </details>
      ))}
    </div>
  );
}
