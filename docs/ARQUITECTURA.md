# Arquitectura

## Flujo general del MVP

```text
                           USUARIO
                              |
                              v
                         +---------+
                         | Next.js |
                         +----+----+
                              |
                         POST /api/chat
                              |
                              v
                     +------------------+
                     |     FastAPI      |
                     |       API        |
                     +--------+---------+
                              |
                              v
                   +----------------------+
                   | DeliberationOrchestrator |
                   +----------+-----------+
                              |
                              v
                       +------------+
                       | TaskRouter |
                       +-----+------+
                              |
                (clasifica y elige 1, 2 o 3 providers)
                              |
                +-------------+-------------+
                |             |             |
                v             v             v
          +----------+  +----------+  +----------+
          |  OpenAI  |  | Anthropic|  |  Gemini  |
          +-----+----+  +----+-----+  +----+-----+
                |             |             |
                +-------------+-------------+
                              |
                              v
                       +------------+
                       | CrossCritic|
                       +-----+------+
                              |
        (si hay >=2 exitosos: cada uno critica a los demas)
                              |
                              v
                  +----------------------+
                  | DisagreementDetector |
                  +-----------+----------+
                              |
           (escanea las criticas por senales de contradiccion)
                              |
                              v
                    +------------------+
                    |   Reevaluator    |
                    +--------+---------+
                              |
      (cada exitoso revisa su PROPIA respuesta con las criticas)
                              |
                              v
                    +------------------+
                    |    Synthesizer   |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |  ChatResponse    |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    | PostgreSQL logs  |
                    +------------------+
```

## Abstracción de providers

```text
                     +----------------+
                     |  LLMProvider   |
                     | generate()     |
                     | analyze()      |
                     | critique()     |
                     +-------+--------+
                             |
          +------------------+------------------+
          |                  |                  |
          v                  v                  v
 +----------------+ +----------------+ +----------------+
 | OpenAIProvider | |AnthropicProvider| | GeminiProvider |
 +----------------+ +----------------+ +----------------+
```

El orquestador depende exclusivamente de `LLMProvider`. Cada adaptador traduce el contrato común al SDK oficial de su proveedor. Esto evita que el router futuro o el sintetizador tengan lógica específica de OpenAI, Anthropic o Gemini.

## Degradación elegante

Cada llamada captura errores del SDK y produce un `LLMResponse` con `error`. `asyncio.gather(..., return_exceptions=True)` permite que un fallo no cancele los demás proveedores. Si existe al menos una respuesta válida, el sistema intenta sintetizar. Si la síntesis falla, el MVP usa como fallback la primera respuesta válida.

## Router inteligente (v2)

`TaskRouter.classify()` clasifica el prompt en `low`/`medium`/`high` usando heurísticas simples (palabras clave y longitud, ver `backend/app/core/router.py`) y decide cuántos providers usar (1/2/3). `select_providers()` elige el subconjunto según `settings.provider_priority` (por defecto el orden de menor a mayor costo por token). El orquestador llama al router en cada `run()`, así que el mismo `DeliberationOrchestrator` sirve tanto para un prompt trivial (1 provider) como para uno complejo (3 providers + síntesis), sin que el endpoint tenga que decidir nada. La decisión de enrutamiento (`complexity`, `routing_reason`) se expone en `ChatResponse` y se persiste en `request_logs` por transparencia.

Esto es deliberadamente una heurística, no un clasificador con IA: mantiene el costo de clasificar cerca de cero y es suficiente para el objetivo del documento de diseño (no gastar 3 modelos en una pregunta simple). Un clasificador más sofisticado (o basado en LLM) puede reemplazar `TaskRouter.classify()` sin tocar el orquestador ni los providers.

## Crítica cruzada (v2)

Si hay al menos 2 respuestas exitosas y `settings.enable_cross_critique` está activo, `DeliberationOrchestrator.run()` lanza una ronda de crítica en paralelo: cada provider que respondió con éxito recibe, vía `CrossCritic` (`backend/app/core/critic.py`), el prompt original y las respuestas de LOS DEMÁS (nunca la propia), y se le pide identificar errores, contradicciones, supuestos, omisiones, ventajas, limitaciones y mejoras — igual que la sección 4.4 del documento de diseño. `CrossCritic` sigue el mismo patrón que `Synthesizer`: no usa el método `critique()` de `LLMProvider` (que sigue siendo un stub sin uso, igual que `analyze()`), construye el prompt de crítica y llama a `provider.generate()`.

Con N respuestas exitosas se hacen N llamadas de crítica (nunca N×(N-1)): cada modelo revisa a todos los demás en una sola llamada. Una crítica que falla (timeout o excepción) no bloquea la síntesis — se registra con `error` y se sigue, igual que el resto del sistema. El `Synthesizer` recibe las críticas exitosas junto con las respuestas originales y las usa para construir la respuesta final, con la misma advertencia de "esto es evidencia, no verdad" que ya aplica a las respuestas de los candidatos. Las críticas quedan expuestas en `ChatResponse.critiques` y persistidas en `request_logs.critiques` (JSONB) por transparencia, y su costo/tokens se suman al total reportado.

## Detección de desacuerdos (v2)

`DisagreementDetector.assess()` (`backend/app/core/disagreement.py`) clasifica el resultado de la ronda de crítica en `not_applicable` (no hubo crítica: menos de 2 exitosos o `enable_cross_critique=false`), `consensus` (hubo crítica y no señala contradicciones) o `disagreement` (al menos una crítica exitosa contiene una señal de contradicción/error).

Decisión de diseño deliberada: en vez de comparar el texto de las respuestas originales entre sí (lo que el documento de diseño desaconseja como método principal — "no depender de coincidencia textual"), la detección escanea el **contenido de las críticas ya generadas en la ronda anterior**. Cada crítica es, por construcción, un análisis semántico hecho por un LLM que ya identificó explícitamente contradicciones y errores; escanear ese texto por palabras clave (mismo estilo heurístico que `TaskRouter`) es más fiel a "considerar el significado" que comparar las respuestas crudas, y no cuesta ninguna llamada adicional — reutiliza una llamada que el sistema ya paga en la crítica cruzada. La contrapartida: sin ronda de crítica no hay una segunda vía de detección por similitud de texto en esta iteración; queda como `not_applicable`.

Cuando se detecta `disagreement`, el `Synthesizer` recibe la evidencia y se le pide resolverla explícitamente en la respuesta final (indicar qué postura es más probable o reconocer la incertidumbre) en vez de promediar o ignorar la discrepancia. El resultado (`disagreement_level`, `disagreement_reason`, `disagreement_evidence`) se expone en `ChatResponse` y se persiste en `request_logs` por transparencia. Este componente **detecta y reporta**, no dispara por sí mismo una nueva ronda de generación ni verificación externa.

## Múltiples rondas de deliberación (v2)

Sección 17 ("Paso 4 — Reevaluación") del documento de diseño: los modelos revisan sus propuestas a partir de las críticas antes de la síntesis final. `Reevaluator` (`backend/app/core/reevaluator.py`) implementa exactamente ese paso, con el mismo patrón que `Synthesizer`/`CrossCritic` (arma un prompt, llama a `provider.generate()`).

Si `settings.enable_reevaluation_round` está activo y la ronda de crítica produjo al menos una crítica exitosa, cada provider que respondió con éxito recibe su propia respuesta previa más TODAS las críticas (que hablan de todos los candidatos, incluida la suya) y produce una respuesta mejorada. El sistema es deliberadamente de **2 rondas de generación** (independiente + reevaluación), no un bucle abierto de N rondas: es exactamente lo que describe el ejemplo del documento (sección 17, "Paso 4" único antes de "Paso 5 — Síntesis"), y mantiene el costo acotado y predecible.

La revisión de cada provider **reemplaza** su respuesta en el conjunto que se usa para la síntesis final; si la reevaluación de un provider falla (timeout o excepción), se conserva su respuesta original de la ronda independiente en su lugar — misma degradación elegante que el resto del sistema. La crítica y la detección de desacuerdos usadas por la síntesis siguen siendo las de ANTES de la reevaluación (igual que en el ejemplo del documento), no se vuelve a criticar el resultado revisado. Las revisiones quedan expuestas en `ChatResponse.revisions` y persistidas en `request_logs.revisions` (JSONB), con su costo/tokens sumados al total.

## Evolución por fases

- **MVP:** generación paralela + síntesis.
- **v2:** router de clasificación y selección dinámica (implementado); crítica cruzada (implementada); detección de desacuerdos (implementada); múltiples rondas de deliberación (implementadas).
- **v3:** herramientas externas pueden consumir los resultados antes de sintetizar.
- **v4:** los logs existentes proporcionan la base para comparar costo, latencia y calidad.

## Decisiones de persistencia

Se usa SQLAlchemy async con `asyncpg`. Alembic gestiona las migraciones desde el principio para que los cambios de esquema de las siguientes fases no dependan de `create_all`.
