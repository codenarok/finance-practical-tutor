"""Application configuration using environment variables."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings loaded from environment variables for secure configuration."""

    app_name: str = Field("Finance Tutor", description="Name of the application")
    secret_key: str = Field(..., description="Secret key for JWT signing")
    algorithm: str = Field("HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(60, description="JWT expiration in minutes")

    database_url: str = Field(..., description="PostgreSQL database URL")
    ollama_base_url: str = Field("http://localhost:11434", description="Base URL for Ollama server")
    ollama_model: str = Field("llama3", description="Model name to use with Ollama")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
