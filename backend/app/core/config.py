"""Pydantic Settings — all environment variables for the IPM backend."""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field

class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    # --- Database ---
    database_url: str = "postgresql+asyncpg://ipm:ipm@postgres:5432/ipm"

    # --- Deployment ---
    environment: str = "development"
    debug: bool = False

    # --- API ---
    api_title: str = "IPM API"
    api_version: str = "0.1.0"
    api_description: str = "Intelligent Project Management API"

    # --- CORS ---
    # Keep the raw environment value as a string to avoid pydantic-settings
    # attempting JSON decoding of complex types during env parsing.
    cors_origins_raw: str = Field(default="http://localhost:3000", env="CORS_ORIGINS")

    # --- MinIO ---
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    # --- Pinecone (vector store; replaces ChromaDB) ---
    # Explicit aliases so Render / Docker env vars always bind (not only auto-generated names).
    pinecone_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("PINECONE_API_KEY"),
    )
    pinecone_index_name: str = Field(
        default="",
        validation_alias=AliasChoices("PINECONE_INDEX"),
    )
    pinecone_cloud: str = Field(default="aws", env="PINECONE_CLOUD")
    # Accept legacy PINECONE_ENVIRONMENT (older docs) as fallback for serverless region.
    pinecone_region: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices("PINECONE_REGION", "PINECONE_ENVIRONMENT"),
    )
    pinecone_index_dimension: int = Field(default=384, env="PINECONE_INDEX_DIMENSION")
    pinecone_auto_create_index: bool = Field(default=False, env="PINECONE_AUTO_CREATE_INDEX")
    pinecone_seed_catalog_on_startup: bool = Field(default=True, env="PINECONE_SEED_CATALOG_ON_STARTUP")

    # --- LLM Provider ---
    llm_provider: str = "groq"  # "groq" | "azure"
    groq_api_key: str = ""
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-02-15-preview"

    # --- Embedding Provider ---
    embedding_provider: str = "local"  # "local" | "openai"
    openai_api_key: str = ""
    embedding_model_local: str = "BAAI/bge-small-en-v1.5"
    embedding_model_openai: str = "text-embedding-ada-002"
    # --- Langfuse (Observability) ---
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # In production, read only OS env (Render dashboard) — avoids an empty committed `.env`
    # shadowing or confusing optional keys. Local dev still loads `.env`.
    model_config = SettingsConfigDict(
        env_file=None if os.environ.get("ENVIRONMENT") == "production" else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    @property
    def cors_origins(self) -> list[str]:
        """Return a list of origins.

        The environment provides a raw string (comma-separated) via `CORS_ORIGINS`.
        This property parses that string into a list for backward compatibility.
        """
        value = self.cors_origins_raw
        if value is None:
            return ["http://localhost:3000"]
        if isinstance(value, str):
            parsed = [origin.strip() for origin in value.split(",")]
            return [origin for origin in parsed if origin]
        if isinstance(value, list):
            return value
        return [str(value)]

    @property
    def pinecone_configured(self) -> bool:
        """True when API key and index name are set (vectors + catalog search enabled)."""
        return bool(self.pinecone_api_key.strip() and self.pinecone_index_name.strip())


settings = Settings()
