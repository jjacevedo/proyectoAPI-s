'use client';

import { useState } from 'react';
import { ChatForm } from '@/components/ChatForm';
import { CritiquesAccordion } from '@/components/CritiquesAccordion';
import { FinalAnswer } from '@/components/FinalAnswer';
import { IndividualResponsesAccordion } from '@/components/IndividualResponsesAccordion';
import { ModelsParticipated } from '@/components/ModelsParticipated';
import { sendChat } from '@/lib/api';
import type { ChatResponse } from '@/types/chat';

export default function Home() {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      setResponse(await sendChat(prompt));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>proyectoAPI-s</h1>
      <p className="subtitle">Orquestación MVP de OpenAI + Claude + Gemini</p>
      <ChatForm prompt={prompt} setPrompt={setPrompt} onSubmit={handleSubmit} loading={loading} />
      {error && <div className="card error">{error}</div>}
      {response && (
        <>
          <FinalAnswer answer={response.final_answer} />
          <ModelsParticipated responses={response.responses} />
          <IndividualResponsesAccordion responses={response.responses} />
          <CritiquesAccordion critiques={response.critiques} />
          <div className="card meta">
            Tokens: {response.total_tokens} · Costo estimado: {response.total_cost_estimated_usd == null ? 'N/D' : `$${response.total_cost_estimated_usd.toFixed(6)}`} · Latencia total: {response.latency_ms.toFixed(0)} ms
          </div>
          <div className="card meta">
            Complejidad detectada: {response.complexity} ({response.routing_reason})
          </div>
        </>
      )}
    </main>
  );
}
