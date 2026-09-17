import type { EvaluateResponse } from '@/types/evaluate';

type Props = {
  evaluation: EvaluateResponse;
};

function formatCost(value: number | null): string {
  return value == null ? 'N/D' : `$${value.toFixed(6)}`;
}

function formatDelta(value: number, unit: string): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(unit === 'ms' ? 0 : 6)} ${unit}`;
}

export function EvaluationPanel({ evaluation }: Props) {
  return (
    <>
      <section className="card">
        <h2>Respuesta de un solo LLM ({evaluation.single_provider})</h2>
        {evaluation.single_error ? (
          <p className="error">{evaluation.single_error}</p>
        ) : (
          <p>{evaluation.single_answer}</p>
        )}
        <p className="meta">
          Modelo: {evaluation.single_model} · Tokens: {evaluation.single_tokens} · Costo: {formatCost(evaluation.single_cost_estimated_usd)} · Latencia: {evaluation.single_latency_ms.toFixed(0)} ms
        </p>
      </section>

      <section className="card">
        <h2>Respuesta multi-LLM (deliberación)</h2>
        <p>{evaluation.multi_answer}</p>
        <p className="meta">
          Tokens: {evaluation.multi_tokens} · Costo: {formatCost(evaluation.multi_cost_estimated_usd)} · Latencia: {evaluation.multi_latency_ms.toFixed(0)} ms
        </p>
      </section>

      <section className="card">
        <h2>Comparación</h2>
        <p className="meta">
          Δ Tokens: {formatDelta(evaluation.token_delta, 'tokens')} · Δ Costo: {evaluation.cost_delta_usd == null ? 'N/D' : formatDelta(evaluation.cost_delta_usd, 'USD')} · Δ Latencia: {formatDelta(evaluation.latency_delta_ms, 'ms')}
        </p>
        {evaluation.judge_error && <p className="error">Juez no disponible: {evaluation.judge_error}</p>}
        {evaluation.judge_verdict && (
          <>
            <p>
              <strong>Veredicto del juez:</strong>{' '}
              {evaluation.judge_verdict === 'multi'
                ? 'la respuesta multi-LLM es mejor'
                : evaluation.judge_verdict === 'single'
                  ? 'la respuesta de un solo LLM es mejor'
                  : 'empate entre ambas respuestas'}
            </p>
            {evaluation.judge_reasoning && <p>{evaluation.judge_reasoning}</p>}
          </>
        )}
      </section>
    </>
  );
}
