from configparser import ConfigParser
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _ini_values() -> dict[str, str]:
    parser = ConfigParser()
    here = Path(__file__).resolve()
    candidates = [
        Path.cwd() / "config.ini",
        here.parents[2] / "config.ini",
        here.parents[1] / "config.ini",
    ]
    for path in candidates:
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
    return {key: value for key, value in values.items() if value}


_INI = _ini_values()
_DEFAULT_CARTO_URL = "https://gcp-us-east1.api.carto.com"
_DEFAULT_TILES = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./events.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:3000"
    querit_api_key: str = _INI.get("querit_api_key", "")
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    carto_api_key: str = _INI.get("carto_api_key", "")
    carto_api_base_url: str = _INI.get("carto_api_base_url", _DEFAULT_CARTO_URL)
    carto_tile_url: str = _INI.get("carto_tile_url", _DEFAULT_TILES)


settings = Settings()
