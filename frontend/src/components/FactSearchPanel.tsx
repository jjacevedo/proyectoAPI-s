import type { FactCheckResultResponse } from '@/types/chat';
import styles from './panels.module.css';

type Props = {
  results: FactCheckResultResponse[];
};

export function FactSearchPanel({ results }: Props) {
  if (results.length === 0) return null;

  return (
    <div className={styles.panel}>
      <h3 className={styles.heading}>Evidencia externa (Wikipedia, independiente de los candidatos)</h3>
      {results.map((result, index) => (
        <details key={`${result.query}-${index}`} className={styles.detail}>
          <summary>{result.query}: {result.error ? 'no verificado' : result.title}</summary>
          {result.error && <p className={styles.error}>{result.error}</p>}
          {result.extract && <p className={styles.response}>{result.extract}</p>}
          {result.url && (
            <p className={styles.meta}>
              <a href={result.url} target="_blank" rel="noreferrer">
                {result.url}
              </a>
            </p>
          )}
        </details>
      ))}
    </div>
  );
}
