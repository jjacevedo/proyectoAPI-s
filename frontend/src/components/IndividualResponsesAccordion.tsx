import type { ProviderResponse } from '@/types/chat';

export function IndividualResponsesAccordion({ responses }: { responses: ProviderResponse[] }) {
  return (
    <section className="card">
      <h2>Respuestas individuales</h2>
      {responses.map((response, index) => (
        <details key={`${response.provider}-${response.model}-${index}`}>
          <summary>{response.provider} / {response.model}</summary>
          {response.error ? <p className="error">{response.error}</p> : <div className="response">{response.content}</div>}
          <p className="meta">
            Tokens: {response.tokens} · Costo: {response.cost_estimated_usd == null ? 'N/D' : `$${response.cost_estimated_usd.toFixed(6)}`} · Latencia: {response.latency_ms.toFixed(0)} ms
          </p>
        </details>
      ))}
    </section>
  );
}
