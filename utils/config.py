# utils/config.py
from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Configuration centralisée de l'API UNIDET AURA."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Environnement et serveur
    app_env: str = "development"
    log_level: str = "INFO"
    frontend_origins: str = ""

    # Base de données
    database_url: SecretStr

    # OpenAI
    openai_api_key: SecretStr
    openai_model: str = "gpt-5-mini"
    openai_embed_model: str = "text-embedding-3-small"
    openai_embed_dimension: int = 1536

    # Recherche documentaire
    retrieval_top_k: int = 5
    web_search_model: str = "gpt-5-mini"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

settings = get_settings()