from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    app_name: str = "LeaseLens API"
    environment: str = "development"
    database_url: str = ""
    cors_origins: str = "http://localhost:5173"
    # Uploaded leases are personal data. The full opt-in-to-save policy is Phase 7 work;
    # until then every upload is deleted after this window, with no way to retain it.
    retention_hours: int = 24
    # Shown in the UI so nobody mistakes an unfinished pipeline for a finished product.
    demo_mode: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
