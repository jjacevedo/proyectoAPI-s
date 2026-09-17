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
                (clasifica y elige 1, 2 o 3 providers,
                 priorizando los gratuitos via provider_priority)
                              |
                +-------------+-------------+
                |             |             |
                v             v             v
          +----------+  +----------+  +----------+
          | Cerebras |  |  Gemini  |  |   Groq   |
          +-----+----+  +----+-----+  +----+-----+
                |             |             |
                +-------------+-------------+
                (OpenAI disponible como respaldo de pago;
                 Anthropic disponible pero inactivo por defecto)
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
      +--------------+--------------+--------------+
      |              |              |               |
      v              v              v               v
+------------+ +------------+ +----------------+ +-------------------------+
|OpenAIProvider| |AnthropicProvider| | GeminiProvider | | OpenAICompatibleProvider|
+------------+ +------------+ +----------------+ +-----------+-------------+
 (activo,       (inactivo por                          |
  de pago)       defecto, de pago)          +-----------+-----------+
                                              |                       |
                                              v                       v
                                       +-------------+       +-----------------+
                                       | GroqProvider|       | CerebrasProvider|
                                       +-------------+       +-----------------+
                                        (gratis)               (gratis)
```

El orquestador depende exclusivamente de `LLMProvider`. Cada adaptador traduce el contrato común al SDK oficial de su proveedor. `GroqProvider` y `CerebrasProvider` comparten una única implementación (`OpenAICompatibleProvider`, en `backend/app/providers/openai_compatible_provider.py`) porque ambos exponen un endpoint `/chat/completions` compatible con la API de OpenAI — solo difieren en `base_url` y `provider_name`. Esto evita que el router o el sintetizador tengan lógica específica de ningún proveedor concreto.

## Degradación elegante

Cada llamada captura errores del SDK y produce un `LLMResponse` con `error`. `asyncio.gather(..., return_exceptions=True)` permite que un fallo no cancele los demás proveedores. Si existe al menos una respuesta válida, el sistema intenta sintetizar. Si la síntesis falla, el MVP usa como fallback la primera respuesta válida.

## Router inteligente (v2)

`TaskRouter.classify()` clasifica el prompt en `low`/`medium`/`high` usando heurísticas simples (palabras clave y longitud, ver `backend/app/core/router.py`) y decide cuántos providers usar (1/2/3). `select_providers()` elige el subconjunto según `settings.provider_priority` (por defecto `cerebras,gemini,groq,openai`: los 3 proveedores gratuitos primero, OpenAI de pago como respaldo solo si el router necesita más providers de los que hay gratis disponibles o si a alguno le falta su API key). El orquestador llama al router en cada `run()`, así que el mismo `DeliberationOrchestrator` sirve tanto para un prompt trivial (1 provider) como para uno complejo (3 providers + síntesis), sin que el endpoint tenga que decidir nada. La decisión de enrutamiento (`complexity`, `routing_reason`) se expone en `ChatResponse` y se persiste en `request_logs` por transparencia.

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

## Ejecución de código y tests (v3, issue #11)

`TaskRouter.classify()` también clasifica `task_type` (`code`/`math`/`general`) por palabras clave, independiente de `complexity`. Cuando `task_type == code` y `settings.enable_code_verification` está activo, el orquestador genera un suite de tests compartido ANTES de ver las respuestas candidatas (`TestCaseGenerator`, `backend/app/core/test_case_generator.py` — mismo patrón que `Synthesizer`), para que la verificación no esté sesgada hacia ninguna implementación. Cada candidato con un bloque de código Python extraíble (`extract_python_code()`) se ejecuta contra ese suite en un subprocess aislado (`CodeVerifier`, `backend/app/core/code_verifier.py`): timeout de pared + límites de recursos (CPU/memoria/procesos/descriptores vía `resource.setrlimit`), entorno mínimo que **no** hereda las variables del backend (las API keys nunca llegan al código ejecutado). Esto **no** es aislamiento a nivel de kernel — es un nivel razonable para un proyecto de un solo usuario, no multi-tenant. El resultado (PASSED/FAILED por candidato) se le pasa al `Synthesizer` como evidencia objetiva, con instrucción explícita de pesarla más que la opinión de cualquier candidato o crítica. Expuesto en `ChatResponse.generated_tests`/`code_verifications` y persistido en `request_logs` (migración `0006_add_code_verification`).

## Motor de cálculo para matemáticas (v3, issue #12)

Mismo principio que la verificación de código, aplicado a aritmética: un valor calculado independientemente es evidencia objetiva mucho más fuerte que la aritmética mental de un LLM. Cuando `TaskRouter.classify()` detecta `task_type == math` (palabras clave como "calcula", "cuánto es", "%", "ecuación" — ver `_MATH_KEYWORDS` en `backend/app/core/router.py`, revisadas solo si no hubo match de `_CODE_KEYWORDS` primero, ya que "escribe una función que calcule..." es una tarea de programación) y `settings.enable_calculation_verification` está activo:

1. `SolverScriptGenerator` (`backend/app/core/solver_script_generator.py`, mismo patrón que `TestCaseGenerator`) pide al provider designado como sintetizador un script Python corto (solo librería estándar) que calcule la respuesta e imprima una línea marcador `__CALC_RESULT__ <numero>`, ANTES de ver las respuestas candidatas.
2. Ese script se ejecuta en el mismo sandbox que la verificación de código (`backend/app/core/sandbox_runner.py` — extraído de `code_verifier.py` en este cambio para que ambas features compartan el subprocess aislado sin duplicar la lógica de límites de recursos/timeout) y su resultado se toma como **valor de referencia**.
3. Para cada candidato exitoso, `CalculationVerifier.verify_candidate()` extrae heurísticamente el ÚLTIMO número que aparece en su respuesta en texto libre (`extract_final_number()` — una aproximación de costo cero, no una interpretación perfecta de cualquier formato numérico) y lo compara contra el valor de referencia con una tolerancia relativa configurable (`settings.calculation_tolerance`).
4. Si no se puede generar el script o no se puede calcular un valor de referencia (timeout, excepción), se registra el fallo sin bloquear la síntesis — misma degradación elegante que el resto del sistema.

El `Synthesizer` recibe los resultados como evidencia objetiva y se le indica corregir explícitamente cualquier número de un candidato que no coincida con la referencia. Expuesto en `ChatResponse.reference_calculation`/`calculation_verifications` y persistido en `request_logs` (migración `0007_add_calc_verification`).

## Búsqueda/RAG para verificación factual (v3, issue #13)

Mismo principio de "evidencia externa objetiva antes que consenso entre modelos", aplicado a hechos puntuales sobre entidades con nombre (personas, lugares, fechas). Cuando `TaskRouter.classify()` detecta `task_type == factual` (palabras clave como "quién fue", "cuándo nació", "capital de" — ver `_FACTUAL_KEYWORDS` en `backend/app/core/router.py`; deliberadamente NO incluye "qué es"/"qué fue" porque es demasiado amplio y cubriría explicaciones conceptuales que los candidatos ya responden bien sin necesidad de una fuente externa) y `settings.enable_fact_search` está activo:

1. `FactQueryGenerator` (`backend/app/core/fact_search.py`, mismo patrón que `TestCaseGenerator`/`SolverScriptGenerator`) pide al provider sintetizador hasta `settings.fact_search_max_queries` consultas de búsqueda cortas y específicas (una por línea) que ayudarían a verificar la afirmación factual de la solicitud original, ANTES de ver las respuestas candidatas.
2. Cada consulta se resuelve contra la **API pública de Wikipedia** (`WikipediaClient`, sin API key ni cuenta: busca la página más relevante y obtiene su resumen vía `/api/rest_v1/page/summary/{title}`), en paralelo, con degradación elegante si una consulta no encuentra resultados o la red falla.
3. El `Synthesizer` recibe los extractos de Wikipedia como evidencia externa (no como veredicto PASS/FAIL binario, a diferencia de la verificación de código/cálculo — un extracto es contexto a citar y contrastar, no un resultado de ejecución determinista) con instrucción de corregir cualquier afirmación de un candidato que la contradiga, y de no tratar el consenso entre candidatos como prueba si contradice la evidencia.

**Limitación de este entorno de desarrollo, documentada honestamente:** el sandbox donde se desarrolló esta función tiene bloqueado por política de red el acceso a `*.wikipedia.org` (confirmado: `403` en el `CONNECT` del proxy). Por eso `WikipediaClient` se probó con mocks de `httpx` (mismo patrón que los tests de los providers LLM, que tampoco hacen llamadas de red reales), y la verificación de la llamada HTTP real a Wikipedia se hizo en `.github/workflows/docker-e2e.yml` (que sí tiene acceso a internet real en el runner de GitHub Actions) con un paso dedicado que falla el job si Wikipedia no devuelve datos utilizables. Expuesto en `ChatResponse.fact_search_results` y persistido en `request_logs` (migración `0008_add_fact_search`).

## Framework de evaluación 1-LLM vs. N-LLM (v4, issue #14)

Endpoint independiente `POST /api/evaluate` (`backend/app/api/routes/evaluate.py`) que responde la pregunta central del proyecto — ¿la deliberación multi-LLM realmente vale el costo/latencia extra frente a un solo LLM? — con una comparación directa en la misma solicitud:

1. `SingleLLMBaseline` (`backend/app/core/evaluator.py`) llama una sola vez al provider configurado como sintetizador (`settings.synthesizer_provider`, o el primero disponible) con el prompt del usuario, sin router ni deliberación — el baseline más simple posible.
2. En paralelo lógico (mismo request), `DeliberationOrchestrator.run()` se ejecuta normalmente con el pipeline completo (router, generación paralela, crítica, síntesis, verificación según `task_type`).
3. Si `settings.enable_evaluation_judge` está activo y el baseline tuvo éxito, `EvaluationJudge` le pide a un tercer LLM (`settings.evaluation_judge_provider`, o el sintetizador) que compare ambas respuestas a ciegas y emita un veredicto estructurado (`__VERDICT__ single|multi|tie` — mismo patrón de marcador que `__CALC_RESULT__`/`__VERIFICATION_SUMMARY__`) con su razonamiento. **Esto es evidencia de un juez LLM, no una verdad objetiva** — a diferencia de la verificación de código/cálculo (deterministas), aquí el "árbitro" es otro modelo con sus propios sesgos; se expone como tal en la respuesta (`judge_verdict`/`judge_reasoning`), nunca como un hecho verificado.
4. La respuesta incluye deltas explícitos (`token_delta`, `cost_delta_usd`, `latency_delta_ms`) calculados con el mismo criterio de totales que `/api/chat` (`_deliberation_totals()`, deliberadamente no compartido con `chat.py` para no arriesgar una regresión en código ya verificado), y se persiste en `evaluation_logs` (migración `0009_add_evaluation_logs`) para poder analizar tendencias a futuro sin depender de logs manuales.

Degradación elegante: si no hay providers configurados, `502`; si el juez falla (rate limit, error de red), la comparación cuantitativa (tokens/costo/latencia) se devuelve igual, solo sin veredicto cualitativo (`judge_error` explica por qué). El frontend expone un checkbox "Modo evaluación" en la página principal (`EvaluationPanel.tsx`) que alterna entre llamar `/api/chat` o `/api/evaluate` con el mismo formulario.

## Dashboard de costos, latencia y calidad (v4, issue #15)

Endpoint de solo lectura `GET /api/dashboard/stats` (`backend/app/api/routes/dashboard.py`) que agrega, sobre los datos ya recolectados en `request_logs` y `evaluation_logs`, las métricas necesarias para responder si la arquitectura multi-LLM aporta beneficios reales frente a su costo — sin introducir ninguna tabla ni columna nueva, es una vista sobre lo que ya existía.

- `backend/app/services/dashboard_stats.py` contiene toda la lógica de agregación como funciones puras (`compute_dashboard_stats()`), deliberadamente separadas de la consulta a la base de datos: el endpoint solo hace `SELECT * FROM request_logs` / `SELECT * FROM evaluation_logs` (carga completa en memoria — aceptable para un proyecto de un solo usuario, no diseñado para escalar a millones de filas) y delega el cálculo a funciones testeables sin necesidad de una base de datos real.
- Métricas expuestas: totales (solicitudes, tokens, costo, latencia promedio), desglose por `task_type` y por `complexity` (conteo, tokens/costo/latencia promedio de cada grupo), tasa de aciertos de la verificación de código y de cálculo (`code_verification_pass_rate`/`calculation_verification_pass_rate`, calculadas sobre el total de verificaciones individuales, no de solicitudes), cantidad de evidencia factual recolectada, y un resumen del framework de evaluación 1-LLM vs. N-LLM (issue #14): cuántas veces ganó cada lado según el juez, empates, veces sin veredicto, y los deltas promedio de tokens/costo/latencia.
- El frontend agrega una página nueva (`frontend/src/app/dashboard/page.tsx`, enlazada desde la página principal) que consume el endpoint y muestra estas métricas en texto plano — sin gráficas todavía, es un panel de observabilidad mínimo viable, no una herramienta de BI.

## Evolución por fases

- **MVP:** generación paralela + síntesis.
- **v2:** router de clasificación y selección dinámica (implementado); crítica cruzada (implementada); detección de desacuerdos (implementada); múltiples rondas de deliberación (implementadas).
- **v3:** ejecución de código y tests (implementada); motor de cálculo (implementado); búsqueda/RAG (implementada, con Wikipedia como fuente).
- **v4:** framework de evaluación 1-LLM vs. N-LLM implementado (`/api/evaluate`, issue #14); dashboard de costos/latencia/calidad implementado (`/api/dashboard/stats`, issue #15); memoria de conversaciones pendiente.

## Decisiones de persistencia

Se usa SQLAlchemy async con `asyncpg`. Alembic gestiona las migraciones desde el principio para que los cambios de esquema de las siguientes fases no dependan de `create_all`.
