from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "LenQuant Website Fabric API"
    api_prefix: str = "/api"
    mongodb_uri: str = ""
    mongodb_db_name: str = "lenquant"
    session_secret: str = "replace-me"
    auth_allowlist_emails: str = ""
    auth_allowlist_domains: str = ""
    backend_cors_origins: str = "http://localhost:3000"

    @property
    def allowlist_emails(self) -> List[str]:
        return [email.strip().lower() for email in self.auth_allowlist_emails.split(",") if email.strip()]

    @property
    def allowlist_domains(self) -> List[str]:
        return [domain.strip().lower() for domain in self.auth_allowlist_domains.split(",") if domain.strip()]

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

