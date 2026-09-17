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

## Evolución por fases

- **MVP:** generación paralela + síntesis.
- **v2:** el mismo contrato añade clasificación, selección dinámica, crítica cruzada y rondas.
- **v3:** herramientas externas pueden consumir los resultados antes de sintetizar.
- **v4:** los logs existentes proporcionan la base para comparar costo, latencia y calidad.

## Decisiones de persistencia

Se usa SQLAlchemy async con `asyncpg`. Alembic gestiona las migraciones desde el principio para que los cambios de esquema de las siguientes fases no dependan de `create_all`.
