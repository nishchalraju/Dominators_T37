"""All API routes under /api."""

from fastapi import APIRouter

from app.api import auth, cases, dashboard, datasets, descriptions, meta, reports, sketches

api_router = APIRouter(prefix="/api")
for module in (meta, auth, dashboard, cases, descriptions, sketches, datasets, reports):
    api_router.include_router(module.router)
