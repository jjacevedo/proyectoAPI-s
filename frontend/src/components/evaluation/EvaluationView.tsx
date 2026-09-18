'use client';

import { useState } from 'react';
import { EvaluationPanel } from '@/components/EvaluationPanel';
import { PromptBar } from '@/components/chat/PromptBar';
import { sendEvaluate } from '@/lib/api';
import type { EvaluateResponse } from '@/types/evaluate';
import { JudgeVerdict } from './JudgeVerdict';
import styles from './EvaluationView.module.css';

export function EvaluationView() {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluateResponse | null>(null);

  async function handleSubmit() {
    const promptSnapshot = prompt;
    if (!promptSnapshot.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await sendEvaluate(promptSnapshot);
      setEvaluation(result);
      setPrompt('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className={styles.header}>
        <div>
          <div className={styles.title}>Modo Evaluación</div>
          <div className={styles.subtitle}>Comparación 1-LLM vs. Multi-LLM</div>
        </div>
        <div className={styles.activePill}>Evaluación activa</div>
      </div>

      <div className={styles.content}>
        {evaluation && (
          <>
            <div className={styles.promptCard}>
              <div className={styles.promptLabel}>Prompt evaluado</div>
              <div className={styles.promptText}>{evaluation.prompt}</div>
            </div>
            <EvaluationPanel evaluation={evaluation} />
            <JudgeVerdict verdict={evaluation.judge_verdict} reasoning={evaluation.judge_reasoning} error={evaluation.judge_error} />
          </>
        )}
        {error && <div className={styles.error}>{error}</div>}
      </div>

      <PromptBar
        prompt={prompt}
        setPrompt={setPrompt}
        onSubmit={handleSubmit}
        loading={loading}
        showModeSelector={false}
        submitLabel="Evaluar"
        placeholder="Escribe un prompt para evaluar..."
      />
    </>
  );
}
