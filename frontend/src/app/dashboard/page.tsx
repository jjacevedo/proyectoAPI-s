'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getDashboardStats } from '@/lib/api';
import type { DashboardStats } from '@/types/dashboard';

function formatCost(value: number | null): string {
  return value == null ? 'N/D' : `$${value.toFixed(6)}`;
}

function formatPercent(value: number | null): string {
  return value == null ? 'N/D' : `${(value * 100).toFixed(0)}%`;
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch((err) => setError(err instanceof Error ? err.message : 'Error desconocido'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main>
      <h1>Dashboard de costos, latencia y calidad</h1>
      <p className="subtitle">
        <Link href="/">&larr; Volver al chat</Link>
      </p>
      {loading && <div className="card">Cargando estadísticas...</div>}
      {error && <div className="card error">{error}</div>}
      {stats && (
        <>
          <section className="card">
            <h2>Totales ({stats.total_requests} solicitudes registradas)</h2>
            <p className="meta">
              Tokens totales: {stats.total_tokens} · Costo total estimado: {formatCost(stats.total_cost_estimated_usd)} · Latencia promedio: {stats.avg_latency_ms == null ? 'N/D' : `${stats.avg_latency_ms.toFixed(0)} ms`}
            </p>
          </section>

          <section className="card">
            <h2>Por tipo de tarea</h2>
            {stats.by_task_type.length === 0 && <p>Sin datos todavía.</p>}
            {stats.by_task_type.map((row) => (
              <p key={row.task_type} className="meta">
                {row.task_type}: {row.count} solicitudes · tokens prom.: {row.avg_tokens.toFixed(0)} · costo prom.: {formatCost(row.avg_cost_usd)} · latencia prom.: {row.avg_latency_ms.toFixed(0)} ms
              </p>
            ))}
          </section>

          <section className="card">
            <h2>Por complejidad</h2>
            {stats.by_complexity.length === 0 && <p>Sin datos todavía.</p>}
            {stats.by_complexity.map((row) => (
              <p key={row.complexity} className="meta">
                {row.complexity}: {row.count} solicitudes · tokens prom.: {row.avg_tokens.toFixed(0)} · costo prom.: {formatCost(row.avg_cost_usd)} · latencia prom.: {row.avg_latency_ms.toFixed(0)} ms
              </p>
            ))}
          </section>

          <section className="card">
            <h2>Verificación externa</h2>
            <p className="meta">
              Tasa de aciertos en código: {formatPercent(stats.verification.code_verification_pass_rate)} · Tasa de aciertos en cálculo: {formatPercent(stats.verification.calculation_verification_pass_rate)} · Evidencia factual recolectada: {stats.verification.fact_search_result_count} resultados
            </p>
          </section>

          <section className="card">
            <h2>Evaluación 1-LLM vs. N-LLM ({stats.evaluation.total_evaluations} comparaciones)</h2>
            <p className="meta">
              Multi-LLM ganó: {stats.evaluation.multi_wins} · Un solo LLM ganó: {stats.evaluation.single_wins} · Empates: {stats.evaluation.ties} · Sin veredicto: {stats.evaluation.judge_unavailable}
            </p>
            <p className="meta">
              Δ Tokens promedio: {stats.evaluation.avg_token_delta == null ? 'N/D' : stats.evaluation.avg_token_delta.toFixed(1)} · Δ Costo promedio: {formatCost(stats.evaluation.avg_cost_delta_usd)} · Δ Latencia promedio: {stats.evaluation.avg_latency_delta_ms == null ? 'N/D' : `${stats.evaluation.avg_latency_delta_ms.toFixed(0)} ms`}
            </p>
          </section>
        </>
      )}
    </main>
  );
}
