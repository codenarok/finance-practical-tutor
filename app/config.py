"""Application configuration using environment variables."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables for secure configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field("Finance Tutor", description="Name of the application")
    secret_key: str = Field(..., min_length=32, description="Secret key for JWT signing (32+ characters)")
    algorithm: str = Field("HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(60, description="JWT expiration in minutes")

    database_url: str = Field(..., description="Database URL (PostgreSQL, or SQLite for local runs)")
    ollama_base_url: str = Field("http://localhost:11434", description="Base URL for Ollama server")
    ollama_model: str = Field("llama3", description="Model name to use with Ollama")

    # Hard caps on every model call: one attempt, bounded input, output and time.
    max_reply_tokens: int = Field(700, description="Most tokens the model may write per reply")
    max_history_chars: int = Field(8000, description="Most earlier conversation text sent to the model")
    model_context_tokens: int = Field(4096, description="Context window requested from Ollama")
    model_timeout_seconds: int = Field(120, description="Longest a single reply may take")

    auth_rate_limit_per_minute: int = Field(10, description="Login/register attempts per client per minute")
    chat_rate_limit_per_minute: int = Field(20, description="Chat messages per user per minute")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
