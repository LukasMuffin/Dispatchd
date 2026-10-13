"""FastAPI application. Run with: uvicorn dispatchd.api.app:app"""

from fastapi import FastAPI

from dispatchd.core.config import get_settings
from dispatchd.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging(get_settings().log_level)
    app = FastAPI(title="dispatchd")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
