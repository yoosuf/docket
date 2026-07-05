"""Application configuration.

Centralizes all environment-driven settings so infrastructure adapters
never read `os.environ` directly. This keeps the rest of the codebase
testable and makes the eventual move to a "real" deployment (containers,
secrets managers, etc.) a one-file change.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DOCKET_", extra="ignore")

    project_name: str = "Docket Document Generation Service"
    api_v1_prefix: str = "/api/v1"

    templates_dir: Path = PROJECT_ROOT / "templates"
    generated_dir: Path = PROJECT_ROOT / "generated"

    # Order matters: when a .doc and .docx exist for the same document
    # type/version, the first matching extension wins (see
    # FilesystemTemplateRepository) — .docx needs no pre-conversion, so
    # it's preferred over legacy .doc.
    template_extensions: tuple[str, ...] = (".docx", ".doc")

    # External binary used for DOCX -> PDF conversion. Must be on PATH,
    # or set DOCKET_LIBREOFFICE_BINARY to an absolute path.
    libreoffice_binary: str = "soffice"
    conversion_timeout_seconds: int = 60

    def ensure_directories(self) -> None:
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
