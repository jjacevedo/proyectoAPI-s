import type { ProviderResponse } from '@/types/chat';

export function RevisionsAccordion({ revisions }: { revisions: ProviderResponse[] }) {
  if (revisions.length === 0) return null;

  return (
    <section className="card">
      <h2>Reevaluación (respuestas revisadas tras la crítica)</h2>
      {revisions.map((revision, index) => (
        <details key={`${revision.provider}-${revision.model}-${index}`}>
          <summary>{revision.provider} / {revision.model}</summary>
          {revision.error ? <p className="error">{revision.error}</p> : <div className="response">{revision.content}</div>}
          <p className="meta">
            Tokens: {revision.tokens} · Costo: {revision.cost_estimated_usd == null ? 'N/D' : `$${revision.cost_estimated_usd.toFixed(6)}`} · Latencia: {revision.latency_ms.toFixed(0)} ms
          </p>
        </details>
      ))}
    </section>
  );
}
