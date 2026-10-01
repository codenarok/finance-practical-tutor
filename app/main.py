"""FastAPI application entrypoint for Finance Tutor."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.controllers import auth_controller, chat_controller
from app.services.database import db_manager


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize database tables on application startup."""

    db_manager.create_all()
    yield


settings = get_settings()
# The UI is served from this same origin, so no CORS headers are needed.
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(auth_controller.router)
app.include_router(chat_controller.router)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def read_root() -> dict[str, str]:
    """Health endpoint for quick checks."""

    return {"message": "Finance Tutor API running"}
