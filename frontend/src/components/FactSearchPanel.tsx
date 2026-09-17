import type { FactCheckResultResponse } from '@/types/chat';

type Props = {
  results: FactCheckResultResponse[];
};

export function FactSearchPanel({ results }: Props) {
  if (results.length === 0) return null;

  return (
    <section className="card">
      <h2>Evidencia externa (Wikipedia, independiente de los candidatos)</h2>
      {results.map((result, index) => (
        <details key={`${result.query}-${index}`}>
          <summary>{result.query}: {result.error ? 'no verificado' : result.title}</summary>
          {result.error && <p className="error">{result.error}</p>}
          {result.extract && <p>{result.extract}</p>}
          {result.url && (
            <p>
              <a href={result.url} target="_blank" rel="noreferrer">
                {result.url}
              </a>
            </p>
          )}
        </details>
      ))}
    </section>
  );
}
