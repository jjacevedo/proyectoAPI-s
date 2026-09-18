'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getDashboardStats } from '@/lib/api';
import { formatCostShort, formatLatency, formatTokens } from '@/lib/format';
import type { DashboardStats } from '@/types/dashboard';
import { EvalComparisonBar } from './EvalComparisonBar';
import { KPICard } from './KPICard';
import { VerificationBar } from './VerificationBar';
import styles from './DashboardView.module.css';

const COMPLEXITY_LABELS: Record<string, string> = {
  low: 'Baja',
  medium: 'Media',
  high: 'Alta',
};
const COMPLEXITY_ORDER = ['low', 'medium', 'high'];

export function DashboardView() {
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
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <div className={styles.headerTop}>
          <div className={styles.title}>Dashboard</div>
          <Link href="/" className={styles.backButton}>
            ← Volver al chat
          </Link>
        </div>
        {stats && <div className={styles.subtitle}>{stats.total_requests} solicitudes registradas</div>}
      </div>

      {loading && <p className={styles.status}>Cargando estadísticas...</p>}
      {error && <p className={styles.errorText}>{error}</p>}

      {stats && (
        <>
          <div className={styles.kpiRow}>
            <KPICard
              label="Costo total estimado"
              value={formatCostShort(stats.total_cost_estimated_usd)}
              sublabel={
                stats.total_requests > 0 && stats.total_cost_estimated_usd != null
                  ? `${formatCostShort(stats.total_cost_estimated_usd / stats.total_requests)} promedio por solicitud`
                  : undefined
              }
            />
            <KPICard
              label="Tokens totales"
              value={formatTokens(stats.total_tokens)}
              sublabel={
                stats.total_requests > 0
                  ? `${formatTokens(Math.round(stats.total_tokens / stats.total_requests))} promedio por solicitud`
                  : undefined
              }
            />
            <KPICard label="Latencia promedio" value={formatLatency(stats.avg_latency_ms)} />
          </div>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Por tipo de tarea</h2>
            {stats.by_task_type.length === 0 ? (
              <p className={styles.status}>Sin datos todavía.</p>
            ) : (
              <div className={styles.taskGrid}>
                {stats.by_task_type.map((row) => (
                  <div key={row.task_type} className={styles.taskCard}>
                    <div className={styles.taskCardHeader}>
                      <span className={styles.taskName}>{row.task_type}</span>
                      <span className={styles.taskCount}>{row.count} solicitudes</span>
                    </div>
                    <div className={styles.taskStats}>
                      <span>Tokens prom: {row.avg_tokens.toFixed(0)}</span>
                      <span>Costo prom: {formatCostShort(row.avg_cost_usd)}</span>
                      <span>Lat: {row.avg_latency_ms.toFixed(0)}ms</span>
                    </div>
                    <div className={styles.proportionTrack}>
                      <div
                        className={styles.proportionFill}
                        style={{ width: `${stats.total_requests > 0 ? (row.count / stats.total_requests) * 100 : 0}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Por complejidad</h2>
            {stats.by_complexity.length === 0 ? (
              <p className={styles.status}>Sin datos todavía.</p>
            ) : (
              <div className={styles.complexityRow}>
                {[...stats.by_complexity]
                  .sort((a, b) => COMPLEXITY_ORDER.indexOf(a.complexity) - COMPLEXITY_ORDER.indexOf(b.complexity))
                  .map((row) => (
                    <div key={row.complexity} className={styles.complexityCard}>
                      <div className={styles.complexityLabel}>{COMPLEXITY_LABELS[row.complexity] ?? row.complexity}</div>
                      <div className={styles.complexityCount}>{row.count}</div>
                      <div className={styles.complexitySub}>
                        {row.avg_tokens.toFixed(0)} tok · {row.avg_latency_ms.toFixed(0)}ms
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </section>

          <div className={styles.bottomGrid}>
            <div className={styles.card}>
              <h2 className={styles.sectionTitle}>Verificación</h2>
              <div className={styles.verificationBars}>
                <VerificationBar label="Código" percent={stats.verification.code_verification_pass_rate} color="green" />
                <VerificationBar label="Cálculo" percent={stats.verification.calculation_verification_pass_rate} color="amber" />
              </div>
              <div className={styles.footerLine}>{stats.verification.fact_search_result_count} resultados de evidencia factual</div>
            </div>

            <div className={styles.card}>
              <h2 className={styles.sectionTitle}>Evaluación 1-LLM vs. N-LLM</h2>
              <div className={styles.footerLine} style={{ marginBottom: 16, marginTop: 0 }}>
                {stats.evaluation.total_evaluations} comparaciones realizadas
              </div>
              <EvalComparisonBar
                multiWins={stats.evaluation.multi_wins}
                singleWins={stats.evaluation.single_wins}
                ties={stats.evaluation.ties}
                judgeUnavailable={stats.evaluation.judge_unavailable}
              />
              <div className={styles.deltaFooter}>
                <span>
                  Δ Tokens prom: {stats.evaluation.avg_token_delta == null ? 'N/D' : stats.evaluation.avg_token_delta.toFixed(1)}
                </span>
                <span>Δ Costo prom: {formatCostShort(stats.evaluation.avg_cost_delta_usd)}</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
