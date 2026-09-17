# Roadmap

## Fase 1 — MVP: Orquestación básica multi-LLM

Implementada en este scaffold:

- FastAPI async.
- Abstracción común `LLMProvider`.
- Providers OpenAI, Anthropic y Gemini.
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
- [ ] `critique()` real y crítica cruzada.
- [ ] Detección de desacuerdos.
- [ ] Múltiples rondas de deliberación.
- [ ] Rate limiting y controles de presupuesto más avanzados.

## Fase 3 — Verificación externa

- Ejecución de código y tests.
- Motor de cálculo para matemáticas.
- Búsqueda y RAG para verificación factual.
- Incorporación de evidencia externa al proceso de síntesis.

## Fase 4 — Evaluación y métricas

- Framework experimental 1-LLM vs N-LLM.
- Métricas de calidad, costo y latencia.
- Dashboard.
- Memoria de conversaciones.
- Modos rápido / deliberación / máxima verificación.

## Principio de evolución

El MVP mantiene los contratos y límites arquitectónicos que permiten incorporar las siguientes fases sin acoplar el orquestador a un proveedor concreto.
