from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.errors import setup_exception_handlers
from app.core.rate_limit import setup_rate_limiting
from app.api.v1 import api_router
from app.db.session import engine, Base
import app.models  # ensure models are registered with Base metadata


def create_application() -> FastAPI:
    # Ensure tables exist for dev/testing
    Base.metadata.create_all(bind=engine)

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup rate limiting and exception handlers
    setup_rate_limiting(app)
    setup_exception_handlers(app)

    # Include API routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get(f"{settings.API_V1_STR}/health", tags=["health"])
    def health_check():
        return {"status": "ok", "service": settings.PROJECT_NAME}

    return app


app = create_application()
