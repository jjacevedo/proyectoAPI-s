import type { EvaluateResponse } from '@/types/evaluate';
import { formatCost, formatDelta, formatTokens } from '@/lib/format';
import styles from './EvaluationPanel.module.css';

type Props = {
  evaluation: EvaluateResponse;
};

export function EvaluationPanel({ evaluation }: Props) {
  return (
    <>
      <div className={styles.grid}>
        <div className={styles.column}>
          <div className={styles.columnHeader}>
            <span className={styles.columnLabel}>Single LLM</span>
            <span className={styles.providerBadge}>{evaluation.single_provider}</span>
          </div>
          {evaluation.single_error ? (
            <p className={styles.errorText}>{evaluation.single_error}</p>
          ) : (
            <div className={styles.answer}>{evaluation.single_answer}</div>
          )}
          <div className={styles.statsRow}>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Tokens</span>
              <span className={styles.statValue}>{formatTokens(evaluation.single_tokens)}</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Costo</span>
              <span className={styles.statValue}>{formatCost(evaluation.single_cost_estimated_usd)}</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Latencia</span>
              <span className={styles.statValue}>{evaluation.single_latency_ms.toFixed(0)}ms</span>
            </div>
          </div>
        </div>

        <div className={styles.column}>
          <div className={styles.columnHeader}>
            <span className={styles.columnLabel}>Multi-LLM</span>
          </div>
          <div className={styles.answer}>{evaluation.multi_answer}</div>
          <div className={styles.statsRow}>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Tokens</span>
              <span className={styles.statValue}>{formatTokens(evaluation.multi_tokens)}</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Costo</span>
              <span className={styles.statValue}>{formatCost(evaluation.multi_cost_estimated_usd)}</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Latencia</span>
              <span className={styles.statValue}>{evaluation.multi_latency_ms.toFixed(0)}ms</span>
            </div>
          </div>
        </div>
      </div>

      <div className={styles.deltaRow}>
        <span>
          Δ Tokens <strong>{formatDelta(evaluation.token_delta, 'tokens')}</strong>
        </span>
        <span>
          Δ Costo{' '}
          <strong>{evaluation.cost_delta_usd == null ? 'N/D' : formatDelta(evaluation.cost_delta_usd, 'USD')}</strong>
        </span>
        <span>
          Δ Latencia <strong>{formatDelta(evaluation.latency_delta_ms, 'ms')}</strong>
        </span>
      </div>
    </>
  );
}
