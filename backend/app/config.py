from configparser import ConfigParser
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_CARTO_URL = "https://gcp-us-east1.api.carto.com"
_DEFAULT_TILES = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"


def _ini_paths() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        Path.cwd() / "config.ini",
        here.parents[2] / "config.ini",
        here.parents[1] / "config.ini",
    ]


def ini_values() -> dict[str, str]:
    parser = ConfigParser()
    for path in _ini_paths():
        if path.is_file():
            parser.read(path, encoding="utf-8")
            break
    values: dict[str, str] = {}
    if parser.has_section("querit"):
        values["querit_api_key"] = parser.get("querit", "api_key", fallback="").strip()
    if parser.has_section("carto"):
        values["carto_api_key"] = parser.get("carto", "api_key", fallback="").strip()
        values["carto_api_base_url"] = parser.get("carto", "api_base_url", fallback="").strip()
        values["carto_tile_url"] = parser.get("carto", "tile_url", fallback="").strip()
    if parser.has_section("openrouter"):
        values["llm_api_key"] = parser.get("openrouter", "api_key", fallback="").strip()
        values["llm_base_url"] = parser.get("openrouter", "base_url", fallback="").strip()
        values["llm_model"] = parser.get("openrouter", "model", fallback="").strip()
    elif parser.has_section("openai"):
        values["llm_api_key"] = parser.get("openai", "api_key", fallback="").strip()
        values["llm_base_url"] = parser.get("openai", "base_url", fallback="").strip()
        values["llm_model"] = parser.get("openai", "model", fallback="").strip()
    return {key: value for key, value in values.items() if value}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    database_url: str = "sqlite:///./events.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:3000"
    querit_api_key: str = ""
    openrouter_api_key: str = ""
    openai_api_key: str = ""
    carto_api_key: str = ""
    carto_api_base_url: str = _DEFAULT_CARTO_URL
    carto_tile_url: str = _DEFAULT_TILES

    def secret(self, name: str) -> str:
        current = str(getattr(self, name, "") or "").strip()
        if current:
            return current
        return ini_values().get(name, "")

    def llm_api_key(self) -> str:
        return (
            self.openrouter_api_key
            or ini_values().get("llm_api_key", "")
            or self.openai_api_key
            or ""
        ).strip()

    def llm_base_url(self) -> str:
        return (ini_values().get("llm_base_url") or "https://openrouter.ai/api/v1").rstrip("/")

    def llm_model(self) -> str:
        return ini_values().get("llm_model") or "openai/gpt-4o-mini"


settings = Settings()
