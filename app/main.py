"""FastAPI application entrypoint for Finance Tutor."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.controllers import auth_controller, chat_controller
from app.services.database import db_manager


settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_controller.router)
app.include_router(chat_controller.router)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def startup_event() -> None:
    """Initialize database tables on application startup."""

    db_manager.create_all()


@app.get("/")
def read_root() -> dict[str, str]:
    """Health endpoint for quick checks."""

    return {"message": "Finance Tutor API running"}
