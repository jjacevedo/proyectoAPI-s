# proyectoAPI-s

Sistema Multi-LLM de Deliberación y Síntesis. MVP con FastAPI + Next.js que consulta OpenAI, Anthropic y Gemini en paralelo y sintetiza una respuesta final.

## Arquitectura MVP

```text
Usuario -> Next.js -> FastAPI -> Orchestrator
                                  |-> OpenAI
                                  |-> Anthropic
                                  |-> Gemini
                                  `-> Synthesizer -> respuesta final
                                           |
                                           `-> PostgreSQL (request_logs)
```

El MVP no implementa todavía router inteligente, crítica cruzada ni verificación externa. Esos componentes quedan preparados como evolución de v2/v3/v4.

## Requisitos

- Docker y Docker Compose
- API keys de uno o más proveedores: OpenAI, Anthropic y/o Gemini

## Quickstart

```bash
cp .env.example .env
# completa las API keys y, si quieres, cambia los modelos

docker compose up --build
```

Abre http://localhost:3000. API: http://localhost:8000. Documentación FastAPI: http://localhost:8000/docs.

El sistema funciona con proveedores parciales: si una key falta o un proveedor falla, los demás pueden continuar. Si todos fallan, `/api/chat` responde 502.

## Tests

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -v
```

Los tests de providers no realizan llamadas de red.

## Persistencia

Alembic gestiona el esquema de PostgreSQL:

```bash
docker compose exec backend alembic upgrade head
```

El contenedor de backend ejecuta la migración automáticamente al arrancar.

## Seguridad

- Las API keys solo viven en backend.
- `.env` está excluido de Git.
- CORS se limita a los orígenes configurados.
- El prompt tiene límite de caracteres.
- Cada proveedor tiene timeout.
- El output está limitado server-side por `MAX_TOKENS_PER_REQUEST`.

No se implementa rate limiting en el MVP; está contemplado para v2.

## Licencia

MIT. Ver [LICENSE](LICENSE).
