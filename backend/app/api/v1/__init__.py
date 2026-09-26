from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.workspaces import router as workspaces_router
from app.api.v1.runs import router as runs_router
from app.api.v1.ingest import router as ingest_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(workspaces_router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(runs_router, prefix="/runs", tags=["runs"])
api_router.include_router(ingest_router, prefix="/ingest", tags=["ingest"])

