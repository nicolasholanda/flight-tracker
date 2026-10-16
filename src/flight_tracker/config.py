from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_token: str
    owner_chat_id: int
    database_path: str = "data/flight-tracker.db"
    check_interval_minutes: int = 60
    check_jitter_seconds: int = 300
    max_active_watches_per_user: int = 5
    max_searches_per_user_per_hour: int = 10
    max_routes_per_run: int = 30
    request_delay_seconds: float = 3
    failure_alert_threshold: int = 3
    currency: str = "BRL"
    language: str = "pt-BR"
    timezone: str = "America/Fortaleza"
