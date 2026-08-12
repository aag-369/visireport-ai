from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "sqlite+aiosqlite:///./visireport.db"

    # Message broker
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "visireport.defects.exchange"
    rabbitmq_queue: str = "visireport.defects.queue"
    rabbitmq_management_url: str = "http://localhost:15672"

    # Auth
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # Cognitive layer
    llm_provider: str = "anthropic"  # "anthropic" | "openai"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Vision
    model_weights_path: str = "/app/weights/best.pt"
    default_tile_size: int = 640
    default_tile_overlap: int = 64
    default_conf_threshold: float = 0.25
    default_iou_threshold: float = 0.45
    max_upload_mb: int = 25
    max_image_dim: int = 4096
    upload_dir: str = "/app/uploads"

    # Misc
    frontend_origin: str = "http://localhost:5173"
    environment: str = "development"
    log_level: str = "INFO"

    # Seed
    seed_engineer_email: str = "engineer@visireport.ai"
    seed_engineer_password: str = "change-me-please"


@lru_cache
def get_settings() -> Settings:
    return Settings()
