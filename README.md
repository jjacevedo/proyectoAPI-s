# proyectoAPI-s

Sistema Multi-LLM de Deliberación y Síntesis. MVP con FastAPI + Next.js que consulta varios LLMs en paralelo y sintetiza una respuesta final.

Por defecto usa proveedores **gratuitos** (Google AI Studio/Gemini y Groq, ambos confirmados funcionando en producción real; NVIDIA NIM y OpenCode Zen también disponibles) para esta fase temprana del proyecto, más OpenAI activo como respaldo (de pago, pero ya verificado funcionando). Cerebras y Anthropic quedan disponibles en el código pero inactivos por defecto (ver [ROADMAP.md](ROADMAP.md) e issue #17 para Anthropic; Cerebras tiene el billing de su cuenta gratuita bloqueado, confirmado con un `402` real).

## Arquitectura MVP

```text
Usuario -> Next.js -> FastAPI -> Orchestrator
                                  |-> Gemini (gratis, confirmado)
                                  |-> Groq (gratis, confirmado)
                                  |-> NVIDIA NIM (gratis, sin modelo confirmado aun)
                                  |-> OpenCode Zen (bloqueado: su tier gratis rechaza terceros)
                                  |-> OpenAI (de pago, respaldo)
                                  `-> Synthesizer -> respuesta final
                                           |
                                           `-> PostgreSQL (request_logs)
```

El MVP no implementa todavía router inteligente, crítica cruzada ni verificación externa. Esos componentes quedan preparados como evolución de v2/v3/v4.

## Requisitos

- Docker y Docker Compose
- API keys de uno o más proveedores gratuitos: Groq ([console.groq.com](https://console.groq.com)) y/o Google AI Studio (Gemini) — ambos confirmados funcionando end-to-end. NVIDIA NIM ([build.nvidia.com](https://build.nvidia.com)) y OpenCode Zen ([opencode.ai](https://opencode.ai)) también están integrados pero con limitaciones reales encontradas en esta sesión (ver `docs/ARQUITECTURA.md`): a NVIDIA aún no se le encuentra un ID de modelo vigente, y OpenCode Zen bloquea su tier gratis para integraciones de terceros (`403 FreeTierError`).
- OpenAI (de pago) y Anthropic/Cerebras (de pago o con billing bloqueado) siguen soportados en el código — agrega su API key en `.env` y agrégalos a `PROVIDER_PRIORITY` para reactivarlos.

## Quickstart

> ¿Vas a correr esto por primera vez o se lo vas a pasar a alguien más?
> Ver [COMO_CORRERLO.md](COMO_CORRERLO.md) — guía paso a paso para Windows, Mac y Linux.

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

Rate limiting y presupuesto diario ya están implementados (`ENABLE_RATE_LIMITING` y
`DAILY_BUDGET_USD` en `.env.example`), pero quedan desactivados por defecto en el MVP.

## Licencia

MIT. Ver [LICENSE](LICENSE).
