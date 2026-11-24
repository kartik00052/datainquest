from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://daginquest:daginquest@localhost:5432/daginquest"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    airflow_base_url: str = "http://localhost:8080"
    airflow_username: str = "admin"
    airflow_password: str = "admin"
    webhook_secret: str = "change-me"
    telegram_bot_token: str = ""
    telegram_allowed_chat_ids: str = ""
    confidence_threshold: float = 0.6
    dedupe_cooldown_minutes: int = 30
    log_max_chars: int = 12000

    @property
    def allowed_chat_ids(self) -> set[int]:
        return {int(x) for x in self.telegram_allowed_chat_ids.split(",") if x.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
