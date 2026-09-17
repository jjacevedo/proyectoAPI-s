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

## Evolución por fases

- **MVP:** generación paralela + síntesis.
- **v2:** router de clasificación y selección dinámica (implementado); pendiente crítica cruzada, detección de desacuerdos y múltiples rondas.
- **v3:** herramientas externas pueden consumir los resultados antes de sintetizar.
- **v4:** los logs existentes proporcionan la base para comparar costo, latencia y calidad.

## Decisiones de persistencia

Se usa SQLAlchemy async con `asyncpg`. Alembic gestiona las migraciones desde el principio para que los cambios de esquema de las siguientes fases no dependan de `create_all`.
