from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fridgetube"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # YouTube
    youtube_api_key: str = ""

    # Gemini
    gemini_api_key: str = ""

    # Sentry
    sentry_dsn: str = ""

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # CORS
    allowed_origins: str = ""

    # Transcript beta (must be false in production)
    transcript_beta: str = "false"

    # JWT
    jwt_secret: str = "dev-secret-change-in-production"

    # Environment
    environment: str = "development"

    model_config = {
        "env_file": "../.env.local",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
