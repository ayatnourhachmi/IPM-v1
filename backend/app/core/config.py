"""Pydantic Settings — all environment variables for the IPM backend."""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


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

    # --- ChromaDB ---
    # Set CHROMA_ENABLED=false on single-process hosts (e.g. Render without a Chroma sidecar).
    chroma_enabled: bool = True
    chroma_host: str = "chromadb"
    chroma_port: int = 8001

    # --- MinIO ---
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    # --- Vector DB ---
    pinecone_api_key: str = ""
    pinecone_environment: str = "us-east1-gcp"

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
    model_config = {"env_file": ".env", "extra": "ignore"}

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


settings = Settings()
