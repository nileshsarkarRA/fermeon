"""
Fermeon — App Settings
Reads configuration from environment variables / .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # Application
    app_name: str = "Fermeon"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # LLM API Keys (optional — users can supply their own)
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    mistral_api_key: Optional[str] = Field(default=None, env="MISTRAL_API_KEY")

    # Ollama (local LLMs)
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")

    # CAD Execution
    cadquery_timeout_seconds: int = Field(default=60, env="CADQUERY_TIMEOUT_SECONDS")
    max_correction_attempts: int = Field(default=3, env="MAX_CORRECTION_ATTEMPTS")
    enable_fallback: bool = Field(default=True, env="ENABLE_FALLBACK")
    default_model: str = Field(default="gemini/gemini-2.0-flash", env="DEFAULT_MODEL")


    # Storage (optional — local file storage is the default)
    use_s3: bool = Field(default=False, env="USE_S3")
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    s3_bucket_name: Optional[str] = Field(default=None, env="S3_BUCKET_NAME")

    # Output directory for generated files
    output_dir: str = Field(default="./outputs", env="OUTPUT_DIR")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Singleton
settings = Settings()
