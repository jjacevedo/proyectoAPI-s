# Roadmap

## Fase 1 — MVP: Orquestación básica multi-LLM

Implementada en este scaffold:

- FastAPI async.
- Abstracción común `LLMProvider`.
- Providers OpenAI, Anthropic y Gemini (implementados originalmente; ver nota abajo sobre el pivote a proveedores gratuitos).
- Ejecución paralela con `asyncio.gather`.
- Degradación elegante ante fallos parciales.
- Synthesizer configurable.
- Persistencia en PostgreSQL mediante SQLAlchemy async + Alembic.
- Frontend Next.js/TypeScript.
- Docker Compose.
- Tests y CI.
- Logging básico de tokens, costo estimado y latencia.

## Fase 2 — Router inteligente y deliberación

- [x] Clasificación de tareas (`TaskRouter`, heurística por palabras clave y longitud).
- [x] Selección dinámica de modelos (1/2/3 según complejidad, orden configurable por costo).
- [x] Crítica cruzada (`CrossCritic`, cada provider exitoso revisa a los demás; se salta con <2 exitosos o `enable_cross_critique=false`).
- [x] Detección de desacuerdos (`DisagreementDetector`, deriva la señal del contenido de las críticas; alimenta al `Synthesizer` cuando detecta contradicción).
- [x] Múltiples rondas de deliberación (`Reevaluator`: cada provider revisa su propia respuesta con las críticas antes de sintetizar; 2 rondas de generación, no un bucle abierto).
- [ ] Rate limiting y controles de presupuesto más avanzados.

## Pivote a proveedores gratuitos

Para evitar depender de créditos de pago durante esta fase temprana (issue #17: Anthropic se quedó sin crédito real en producción), se agregaron **Groq** y **Cerebras** (`backend/app/providers/groq_provider.py`, `cerebras_provider.py`, ambos comparten `OpenAICompatibleProvider`) como proveedores gratuitos elegidos del catálogo [free-llm-api-resources](https://github.com/raullenchai/free-llm-api-resources), y el modelo por defecto de Gemini pasó de uno de pago (`gemini-3.8-flash`) a uno del tier gratuito de Google AI Studio (`gemini-3.1-flash-lite`). `provider_priority` prioriza ahora los 3 gratuitos; OpenAI se mantiene activo como respaldo de pago (ya verificado funcionando) y Anthropic queda disponible pero inactivo por defecto. Ningún proveedor se eliminó — reactivar Anthropic es tan simple como agregarle una API key.

## Fase 3 — Verificación externa

- [x] Ejecución de código y tests (`TestCaseGenerator` + `CodeVerifier`, sandbox subprocess; issue #11).
- [x] Motor de cálculo para matemáticas (`SolverScriptGenerator` + `CalculationVerifier`, comparte el sandbox con la verificación de código vía `sandbox_runner.py`; issue #12).
- [x] Búsqueda y RAG para verificación factual (`FactQueryGenerator` + `WikipediaClient`, API pública de Wikipedia sin key; issue #13).
- [x] Incorporación de evidencia externa al proceso de síntesis (código, cálculo y hechos, los 3 con el mismo principio: generar evidencia independiente ANTES de ver los candidatos).

## Fase 4 — Evaluación y métricas

- [x] Framework experimental 1-LLM vs N-LLM (`POST /api/evaluate`, `SingleLLMBaseline` + `EvaluationJudge` como juez LLM, deltas de tokens/costo/latencia, persistido en `evaluation_logs`; issue #14).
- [x] Dashboard de costos, latencia y calidad (`GET /api/dashboard/stats` agregando `request_logs`/`evaluation_logs`, página `/dashboard` en el frontend; issue #15).
- [ ] Memoria de conversaciones.
- [ ] Modos rápido / deliberación / máxima verificación.

## Principio de evolución

El MVP mantiene los contratos y límites arquitectónicos que permiten incorporar las siguientes fases sin acoplar el orquestador a un proveedor concreto.
