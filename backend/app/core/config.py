from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Distributed Job Scheduler"
    API_V1_STR: str = "/api/v1"

    # --- Database (override via .env in production) ---
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"          # dev default only — set via .env in production
    POSTGRES_DB: str = "job_scheduler"
    POSTGRES_PORT: str = "5432"

    # --- JWT ---
    # REQUIRED in production: generate with `python -c "import secrets; print(secrets.token_hex(32))"`
    # Set this in your .env file — never commit a real value here.
    SECRET_KEY: str = "dev-only-insecure-key-change-before-deploying"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    @property
    def async_database_uri(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def sync_database_uri(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()

