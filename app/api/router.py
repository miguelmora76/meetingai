"""Top-level API router — aggregates all sub-routers."""

from fastapi import APIRouter

from app.api.admin import router as admin_router
from app.api.docs import router as docs_router
from app.api.health import router as health_router
from app.api.incidents import router as incidents_router
from app.api.meetings import router as meetings_router
from app.api.search import router as search_router
from app.api.slack_router import router as slack_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(admin_router)
api_router.include_router(meetings_router)
api_router.include_router(incidents_router)
api_router.include_router(docs_router)
api_router.include_router(search_router)
api_router.include_router(slack_router)
