import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int = 0) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    default_user_id: str | None
    user_id: str | None
    import_api_token: str
    sessions_csv_path: str | None
    auto_import_sessions_on_startup: bool
    sessions_csv_poll_seconds: int
    ollama_url: str
    ollama_model: str
    ollama_timeout_seconds: int

    @property
    def resolved_user_id(self) -> str | None:
        return self.user_id or self.default_user_id

    @property
    def default_user_uuid(self) -> UUID | None:
        if not self.default_user_id:
            return None
        return UUID(self.default_user_id)

    def require_database_url(self) -> str:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL missing")
        return self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL"),
        default_user_id=os.getenv("DEFAULT_USER_ID"),
        user_id=os.getenv("USER_ID"),
        import_api_token=os.getenv("IMPORT_API_TOKEN", "").strip(),
        sessions_csv_path=os.getenv("SESSIONS_CSV_PATH"),
        auto_import_sessions_on_startup=_env_bool("AUTO_IMPORT_SESSIONS_ON_STARTUP"),
        sessions_csv_poll_seconds=_env_int("SESSIONS_CSV_POLL_SECONDS"),
        ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3"),
        ollama_timeout_seconds=_env_int("OLLAMA_TIMEOUT_SECONDS", 90),
    )
