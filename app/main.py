"""
EngineerAI — FastAPI application factory.

An AI engineering assistant that transcribes meetings, analyzes incidents,
indexes knowledge-base documents, and answers questions using RAG.
"""

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.config.settings import get_settings
from app.db.session import engine
from app.limiter import limiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    settings = get_settings()
    logger.info("=" * 60)
    logger.info("EngineerAI starting up")
    logger.info(f"  LLM Provider:        {settings.llm_provider}")
    logger.info(f"  Summarization model: {settings.summarization_model}")
    logger.info(f"  Extraction model:    {settings.extraction_model}")
    logger.info(f"  Whisper mode:        {settings.whisper_mode}")
    logger.info(f"  Slack enabled:       {settings.slack_enabled}")
    logger.info(f"  CORS origins:        {settings.allowed_origins_list}")
    logger.info("=" * 60)
    yield
    logger.info("EngineerAI shutting down")
    await engine.dispose()


app = FastAPI(
    title="EngineerAI",
    description=(
        "AI Engineering Assistant — Upload meeting recordings, analyze incidents, "
        "index knowledge-base documents, and ask questions using RAG."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — restrict to configured origins
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach a unique request ID to every request and echo it in the response."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — return generic 500, log full traceback."""
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Expose Prometheus metrics at /metrics
Instrumentator().instrument(app).expose(app)

# Mount all API routes — MUST come before StaticFiles mount
app.include_router(api_router)

# Serve the built React frontend — must be last so the catch-all doesn't intercept API routes
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
else:
    logger.warning(
        "frontend/dist not found — static file serving disabled. "
        "Run 'npm run build' inside frontend/ to enable it."
    )
