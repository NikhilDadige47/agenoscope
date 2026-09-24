from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address)


def setup_rate_limiting(app: FastAPI) -> None:
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Too many requests. Please slow down.",
                    "details": str(exc.detail)
                }
            }
        )
