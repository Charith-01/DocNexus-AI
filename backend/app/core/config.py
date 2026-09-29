"""Application configuration loaded from environment variables."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Configuration shared across the DocNexus AI backend."""

    APP_NAME: str = "DocNexus AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    MONGODB_URI: SecretStr
    MONGODB_DB_NAME: str = "docnexus"
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, gt=0)
    MAX_UPLOAD_SIZE_MB: int = Field(default=20, gt=0)
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHROMA_PERSIST_DIR: Path = BACKEND_DIR.parent / "storage" / "chroma"
    CHROMA_COLLECTION_NAME: str = "docnexus_chunks"
    RETRIEVAL_CHUNK_SIZE: int = Field(default=500, gt=0)
    RETRIEVAL_CHUNK_OVERLAP: int = Field(default=100, ge=0)
    RETRIEVAL_TOP_K: int = Field(default=5, gt=0, le=20)
    HYBRID_SEMANTIC_WEIGHT: float = Field(default=0.6, ge=0)
    HYBRID_BM25_WEIGHT: float = Field(default=0.4, ge=0)

    @field_validator("CHROMA_PERSIST_DIR", mode="after")
    @classmethod
    def resolve_chroma_path(cls, value: Path) -> Path:
        return value if value.is_absolute() else (BACKEND_DIR / value).resolve()

    @model_validator(mode="after")
    def validate_retrieval_settings(self) -> "Settings":
        if self.RETRIEVAL_CHUNK_OVERLAP >= self.RETRIEVAL_CHUNK_SIZE:
            raise ValueError("RETRIEVAL_CHUNK_OVERLAP must be smaller than chunk size")
        total = self.HYBRID_SEMANTIC_WEIGHT + self.HYBRID_BM25_WEIGHT
        if abs(total - 1.0) > 1e-6:
            raise ValueError("Hybrid retrieval weights must sum to 1")
        return self

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
