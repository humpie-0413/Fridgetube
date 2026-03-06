import logging
import os

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import router as api_router
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sentry
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        environment=settings.environment,
    )

app = FastAPI(
    title="FridgeTube API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — ALLOWED_ORIGINS 환경변수에서 읽기 (쉼표 구분)
_allowed_raw = os.getenv("ALLOWED_ORIGINS", "")
_allowed_origins = [o.strip() for o in _allowed_raw.split(",") if o.strip()]
if not _allowed_origins:
    _allowed_origins = [settings.frontend_url]
if settings.environment == "development":
    _allowed_origins.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/v1")


@app.get("/health")
async def health_check():
    """Render 헬스체크용. DB와 Redis 연결 상태를 확인한다."""
    result: dict = {"status": "ok", "db": "unknown", "redis": "unknown"}

    # DB check
    try:
        from database import engine
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        result["db"] = "connected"
    except Exception as e:
        result["db"] = f"error: {type(e).__name__}"
        result["status"] = "degraded"

    # Redis check
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()
        result["redis"] = "connected"
    except Exception as e:
        result["redis"] = f"error: {type(e).__name__}"
        result["status"] = "degraded"

    return result


@app.get("/debug/sentry")
async def debug_sentry():
    """Sentry 연동 테스트. 프로덕션에서는 비활성화 권장."""
    if settings.environment == "production":
        return {"error": "disabled in production"}
    raise Exception("Sentry test from FridgeTube")
