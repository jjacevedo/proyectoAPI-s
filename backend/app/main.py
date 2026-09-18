from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.chat import router as chat_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.evaluate import router as evaluate_router
from app.api.routes.health import router as health_router
from app.config import settings

app = FastAPI(title="proyectoAPI-s", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(evaluate_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
