from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import get_settings
from src.interfaces.http.routers import audit, auth, evidences, inspections, sync

settings = get_settings()

app = FastAPI(
    title="Inspections API",
    version="0.1.0",
    description="Offline-first inspections system — Clean Architecture",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(inspections.router)
app.include_router(evidences.router)
app.include_router(sync.router)
app.include_router(audit.router)


@app.get("/healthz", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", tags=["health"])
async def readiness_check() -> dict[str, str]:
    # TODO (iter 2): check DB + Redis connectivity
    return {"status": "ok"}
