from datetime import datetime, timedelta, timezone

import jwt
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://autoqa:autoqa@localhost:5432/autoqa"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    credentials_encryption_key: str = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    artifacts_dir: str = "./artifacts"
    crawl_max_pages: int = 50
    crawl_max_depth: int = 3
    default_parallel_workers: int = 4
    max_parallel_workers: int = 8
    log_level: str = "INFO"

    auth_mode: str = "dev"
    jwt_secret: str = "change-me-in-production-use-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_exp_hours: int = 24
    session_cookie_name: str = "autoqa_session"
    frontend_url: str = "http://localhost:3000"
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_discovery_url: str = ""
    oidc_redirect_uri: str = "http://localhost:8000/api/auth/callback"
    billing_enforcement: bool = True
    stripe_webhook_secret: str = ""


settings = Settings()


def create_access_token(user_id: str, email: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_exp_hours)
    payload = {"sub": user_id, "email": email, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
