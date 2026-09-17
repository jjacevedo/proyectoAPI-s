import type { CritiqueResponse } from '@/types/chat';

export function CritiquesAccordion({ critiques }: { critiques: CritiqueResponse[] }) {
  if (critiques.length === 0) return null;

  return (
    <section className="card">
      <h2>Crítica cruzada</h2>
      {critiques.map((critique, index) => (
        <details key={`${critique.provider}-${critique.model}-${index}`}>
          <summary>
            {critique.provider} / {critique.model} revisa: {critique.reviewed_providers.join(', ') || 'N/D'}
          </summary>
          {critique.error ? <p className="error">{critique.error}</p> : <div className="response">{critique.content}</div>}
          <p className="meta">
            Tokens: {critique.tokens} · Costo: {critique.cost_estimated_usd == null ? 'N/D' : `$${critique.cost_estimated_usd.toFixed(6)}`} · Latencia: {critique.latency_ms.toFixed(0)} ms
          </p>
        </details>
      ))}
    </section>
  );
}
