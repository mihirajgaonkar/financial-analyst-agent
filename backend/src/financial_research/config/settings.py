from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Financial Research Agent"
    environment: str = "development"

    sec_user_agent: str = Field(
        default="Financial Research Agent contact@example.com",
        description="SEC requires a descriptive User-Agent with contact information.",
    )
    fred_api_key: str | None = None
    market_data_provider: str = "alpha_vantage"
    alpha_vantage_api_key: str | None = None
    database_url: str = "postgresql+psycopg://financial_research:financial_research@localhost:5432/financial_research"
    embedding_provider: str = "none"
    embedding_model: str | None = None
    research_timeout_seconds: int = 60

    llm_provider: str = "groq"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-70b-versatile"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openrouter_api_key: str | None = None
    openrouter_model: str = "nvidia/nemotron-3-super"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    google_api_key: str | None = None
    google_model: str = "gemini-3.6-flash"
    ollama_model: str = "llama3.1"
    ollama_base_url: str = "http://localhost:11434"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
