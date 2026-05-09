"""Application configuration.

We use `pydantic-settings` to make required environment variables explicit and
fail fast on startup if any of them are missing or malformed. The original
implementation read os.environ inline at module import time, which silently
produced DSNs like `postgresql+asyncpg://None:None@None:None/None` when
variables were absent — those errors only surfaced at the first DB query.

`@lru_cache` ensures the Settings object is built exactly once per process.
This matters for the Celery worker, where settings are accessed from many task
invocations and we don't want to re-validate on every call.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolved at import time so it is stable regardless of CWD (Alembic, Celery,
# uvicorn all start from different working directories).
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="PGPORT")
    postgres_db: str = Field(alias="POSTGRES_DB")

    # The original code looked up `REDIS_URL`, but `.env.dev` only defines
    # `CELERY_BROKER_URL`. Keep the canonical Celery name and treat REDIS_URL
    # as a fallback for environments that prefer it.
    celery_broker_url: str = Field(
        default="redis://backend-redis:6379/0",
        alias="CELERY_BROKER_URL",
    )

    storage_dir: Path = Field(default=BACKEND_ROOT / "storage" / "files")

    # Hard upper bound on streaming text reads during metadata extraction.
    # Without this, a 5 GB log file uploaded as text/plain would OOM the
    # worker. Chosen to be larger than any realistic legitimate text file but
    # small enough that we won't exhaust worker memory.
    text_metadata_byte_limit: int = 5 * 1024 * 1024

    # Threshold above which the scanner flags a file as suspiciously large.
    # Mirrors the original behaviour (10 MB) — kept as config so it's tunable
    # without code changes.
    suspicious_size_bytes: int = 10 * 1024 * 1024

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton accessor for settings.

    Tests can override this via FastAPI's `dependency_overrides` to inject a
    Settings instance pointing at a sandbox DB / temp storage dir.
    """
    return Settings()  # type: ignore[call-arg]
