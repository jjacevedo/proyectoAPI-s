import type { ProviderResponse } from '@/types/chat';

export function ModelsParticipated({ responses }: { responses: ProviderResponse[] }) {
  return (
    <section className="card">
      <h2>Modelos participantes</h2>
      <div className="badges">
        {responses.map((response, index) => (
          <span className={`badge ${response.error ? 'error' : ''}`} key={`${response.provider}-${response.model}-${index}`}>
            {response.provider}/{response.model}{response.error ? ' · error' : ''}
          </span>
        ))}
      </div>
    </section>
  );
}
