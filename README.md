# proyectoAPI-s

Sistema Multi-LLM de Deliberación y Síntesis. MVP con FastAPI + Next.js que consulta varios LLMs en paralelo y sintetiza una respuesta final.

Por defecto usa proveedores **gratuitos** (Cerebras, Google AI Studio/Gemini, Groq, NVIDIA NIM) para esta fase temprana del proyecto, más OpenAI activo como respaldo (de pago, pero ya verificado funcionando). Anthropic queda disponible pero inactivo por defecto (ver [ROADMAP.md](ROADMAP.md) e issue #17).

## Arquitectura MVP

```text
Usuario -> Next.js -> FastAPI -> Orchestrator
                                  |-> Cerebras (gratis)
                                  |-> Gemini (gratis)
                                  |-> Groq (gratis)
                                  |-> NVIDIA NIM (gratis)
                                  |-> OpenAI (de pago, respaldo)
                                  `-> Synthesizer -> respuesta final
                                           |
                                           `-> PostgreSQL (request_logs)
```

El MVP no implementa todavía router inteligente, crítica cruzada ni verificación externa. Esos componentes quedan preparados como evolución de v2/v3/v4.

## Requisitos

- Docker y Docker Compose
- API keys de uno o más proveedores gratuitos: Groq ([console.groq.com](https://console.groq.com)), Cerebras ([cloud.cerebras.ai](https://cloud.cerebras.ai)), NVIDIA NIM ([build.nvidia.com](https://build.nvidia.com)) y/o Google AI Studio (Gemini). Ninguno debería requerir tarjeta de crédito, pero confírmalo en tu propio registro.
- **Nota sobre la variable de Groq:** por decisión explícita del dueño del repo, la variable de entorno/secret se llama `ROQ_API_KEY` (sin la primera "G"), no `GROQ_API_KEY`. `app/config.py` lee ese nombre exacto vía alias — no es un error de este README.
- OpenAI (de pago) y Anthropic (de pago) siguen soportados — agrega su API key en `.env` para reactivarlos.

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
