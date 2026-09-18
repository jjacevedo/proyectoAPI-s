import type { CritiqueResponse } from '@/types/chat';
import styles from './panels.module.css';

export function CritiquesAccordion({ critiques }: { critiques: CritiqueResponse[] }) {
  if (critiques.length === 0) return null;

  return (
    <div className={styles.panel}>
      <h3 className={styles.heading}>Crítica cruzada</h3>
      {critiques.map((critique, index) => (
        <details key={`${critique.provider}-${critique.model}-${index}`} className={styles.detail}>
          <summary>
            {critique.provider} / {critique.model} revisa: {critique.reviewed_providers.join(', ') || 'N/D'}
          </summary>
          {critique.error ? (
            <p className={styles.error}>{critique.error}</p>
          ) : (
            <div className={styles.response}>{critique.content}</div>
          )}
          <p className={styles.meta}>
            Tokens: {critique.tokens} · Costo: {critique.cost_estimated_usd == null ? 'N/D' : `$${critique.cost_estimated_usd.toFixed(6)}`} · Latencia: {critique.latency_ms.toFixed(0)} ms
          </p>
        </details>
      ))}
    </div>
  );
}
