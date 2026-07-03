import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.api.router import api_router
from app.scheduler.cron_scheduler import CronScheduler
from app.scheduler.retry_promoter import RetryPromoter

logging.basicConfig(level=logging.INFO)

cron_scheduler = CronScheduler(tick_interval=30)
retry_promoter = RetryPromoter(tick_interval=15)

# Rate limiter — uses client IP as key.
# Allows 100 requests/minute per IP to prevent API abuse.
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background services on app startup, shut them down on exit."""
    await cron_scheduler.start()
    await retry_promoter.start()
    yield
    await retry_promoter.stop()
    await cron_scheduler.stop()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Production-quality Distributed Job Scheduler API. "
        "Supports async job queues, cron scheduling, retry policies, "
        "worker coordination, and Dead Letter Queue management."
    ),
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to known frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["health"], summary="Health check")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
