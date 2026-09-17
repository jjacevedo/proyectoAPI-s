'use client';

import Link from 'next/link';
import { useState } from 'react';
import { CalculationVerificationPanel } from '@/components/CalculationVerificationPanel';
import { ChatForm } from '@/components/ChatForm';
import { CodeVerificationPanel } from '@/components/CodeVerificationPanel';
import { CritiquesAccordion } from '@/components/CritiquesAccordion';
import { DisagreementNotice } from '@/components/DisagreementNotice';
import { EvaluationPanel } from '@/components/EvaluationPanel';
import { FactSearchPanel } from '@/components/FactSearchPanel';
import { FinalAnswer } from '@/components/FinalAnswer';
import { IndividualResponsesAccordion } from '@/components/IndividualResponsesAccordion';
import { ModelsParticipated } from '@/components/ModelsParticipated';
import { RevisionsAccordion } from '@/components/RevisionsAccordion';
import { sendChat, sendEvaluate } from '@/lib/api';
import type { ChatResponse } from '@/types/chat';
import type { EvaluateResponse } from '@/types/evaluate';

export default function Home() {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [evaluateMode, setEvaluateMode] = useState(false);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    setResponse(null);
    setEvaluation(null);
    try {
      if (evaluateMode) {
        setEvaluation(await sendEvaluate(prompt));
      } else {
        setResponse(await sendChat(prompt));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>proyectoAPI-s</h1>
      <p className="subtitle">Orquestación MVP de Cerebras + Gemini + Groq (gratis) + OpenAI</p>
      <p className="subtitle">
        <Link href="/dashboard">Ver dashboard de costos, latencia y calidad &rarr;</Link>
      </p>
      <label className="card meta" style={{ display: 'block' }}>
        <input
          type="checkbox"
          checked={evaluateMode}
          onChange={(event) => setEvaluateMode(event.target.checked)}
        />{' '}
        Modo evaluación: comparar 1 LLM vs. deliberación multi-LLM
      </label>
      <ChatForm prompt={prompt} setPrompt={setPrompt} onSubmit={handleSubmit} loading={loading} />
      {error && <div className="card error">{error}</div>}
      {evaluation && <EvaluationPanel evaluation={evaluation} />}
      {response && (
        <>
          <FinalAnswer answer={response.final_answer} />
          <ModelsParticipated responses={response.responses} />
          <IndividualResponsesAccordion responses={response.responses} />
          <CritiquesAccordion critiques={response.critiques} />
          <RevisionsAccordion revisions={response.revisions} />
          <CodeVerificationPanel
            generatedTests={response.generated_tests}
            verifications={response.code_verifications}
          />
          <CalculationVerificationPanel
            referenceCalculation={response.reference_calculation}
            verifications={response.calculation_verifications}
          />
          <FactSearchPanel results={response.fact_search_results} />
          <div className="card meta">
            Tokens: {response.total_tokens} · Costo estimado: {response.total_cost_estimated_usd == null ? 'N/D' : `$${response.total_cost_estimated_usd.toFixed(6)}`} · Latencia total: {response.latency_ms.toFixed(0)} ms
          </div>
          <div className="card meta">
            Complejidad detectada: {response.complexity} ({response.routing_reason}) · Tipo de tarea: {response.task_type}
          </div>
          <DisagreementNotice
            disagreement_level={response.disagreement_level}
            disagreement_reason={response.disagreement_reason}
            disagreement_evidence={response.disagreement_evidence}
          />
        </>
      )}
    </main>
  );
}
