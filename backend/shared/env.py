from pydantic_settings import BaseSettings
from typing import Optional
import sys

class Settings(BaseSettings):
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    TOKEN_ENCRYPTION_KEY: str
    MONGODB_URI: str
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "gemma3"
    LLM_PROVIDER: str = "ollama"  # or "openai_compat"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    SENTRY_DSN: Optional[str] = None
    TEMPORAL_ADDRESS: str = "localhost:7233"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

try:
    settings = Settings()
except Exception as e:
    print(f"❌ Invalid environment variables: {e}")
    sys.exit(1)
