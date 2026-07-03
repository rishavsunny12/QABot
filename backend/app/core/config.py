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


settings = Settings()
