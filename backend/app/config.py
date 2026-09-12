from configparser import ConfigParser
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_CARTO_URL = "https://gcp-us-east1.api.carto.com"
_DEFAULT_TILES = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"


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
        values["page_char_limit"] = parser.get("querit", "page_char_limit", fallback="4000").strip()
        values["result_count"] = parser.get("querit", "result_count", fallback="100").strip()
        values["crawl_timeout"] = parser.get("querit", "crawl_timeout", fallback="8").strip()
        values["contents_batch"] = parser.get("querit", "contents_batch", fallback="8").strip()
        values["fetch_concurrency"] = parser.get("querit", "fetch_concurrency", fallback="10").strip()
        values["search_concurrency"] = parser.get("querit", "search_concurrency", fallback="10").strip()
    if parser.has_section("carto"):
        values["carto_api_key"] = parser.get("carto", "api_key", fallback="").strip()
        values["carto_api_base_url"] = parser.get("carto", "api_base_url", fallback="").strip()
        values["carto_tile_url"] = parser.get("carto", "tile_url", fallback="").strip()
    if parser.has_section("mapbox"):
        values["mapbox_api_key"] = parser.get("mapbox", "api_key", fallback="").strip()
    if parser.has_section("openrouter"):
        values["llm_api_key"] = parser.get("openrouter", "api_key", fallback="").strip()
        values["llm_base_url"] = parser.get("openrouter", "base_url", fallback="").strip()
        values["llm_model"] = parser.get("openrouter", "model", fallback="").strip()
        values["llm_provider"] = parser.get("openrouter", "provider", fallback="").strip()
        values["llm_reasoning"] = parser.get("openrouter", "reasoning", fallback="").strip()
        values["llm_concurrency"] = parser.get("openrouter", "llm_concurrency", fallback="8").strip()
    elif parser.has_section("openai"):
        values["llm_api_key"] = parser.get("openai", "api_key", fallback="").strip()
        values["llm_base_url"] = parser.get("openai", "base_url", fallback="").strip()
        values["llm_model"] = parser.get("openai", "model", fallback="").strip()
    if parser.has_section("database"):
        values["database_url"] = parser.get("database", "url", fallback="").strip()
    return {key: value for key, value in values.items() if value}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    database_url: str = ""
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    querit_api_key: str = ""
    openrouter_api_key: str = ""
    openai_api_key: str = ""
    carto_api_key: str = ""
    carto_api_base_url: str = _DEFAULT_CARTO_URL
    carto_tile_url: str = _DEFAULT_TILES
    mapbox_api_key: str = ""

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
        return ini_values().get("llm_model") or "inception/mercury-2.5"

    def llm_providers(self) -> list[str]:
        raw = ini_values().get("llm_provider") or "inception"
        return [part.strip() for part in raw.replace(";", ",").split(",") if part.strip()]

    def llm_provider_prefs(self, *, require_parameters: bool) -> dict:
        prefs: dict = {"require_parameters": require_parameters}
        providers = self.llm_providers()
        if providers:
            prefs["order"] = providers
            prefs["only"] = providers
            prefs["allow_fallbacks"] = False
        return prefs

    def llm_reasoning(self) -> str:
        allowed = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}
        raw = (ini_values().get("llm_reasoning") or "none").strip().lower()
        return raw if raw in allowed else "low"

    def page_char_limit(self) -> int:
        try:
            return max(500, min(20000, int(ini_values().get("page_char_limit") or 4000)))
        except ValueError:
            return 4000

    def result_count(self) -> int:
        return self._clamped_int("result_count", 100, 1, 100)

    def crawl_timeout(self) -> int:
        return self._clamped_int("crawl_timeout", 8, 3, 30)

    def contents_batch(self) -> int:
        return self._clamped_int("contents_batch", 8, 1, 20)

    def fetch_concurrency(self) -> int:
        return self._clamped_int("fetch_concurrency", 10, 1, 16)

    def search_concurrency(self) -> int:
        return self._clamped_int("search_concurrency", 10, 1, 10)

    def llm_concurrency(self) -> int:
        return self._clamped_int("llm_concurrency", 8, 1, 8)

    def _clamped_int(self, key: str, default: int, lo: int, hi: int) -> int:
        try:
            return max(lo, min(hi, int(ini_values().get(key) or default)))
        except ValueError:
            return default


settings = Settings()
