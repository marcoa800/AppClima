"""Configuración central. Todo lo que dependa del entorno pasa por aquí."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APPCLIMA_",
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = REPO_ROOT / "data"
    user_agent: str = "AppClima/0.1 (proyecto educativo de ingenieria de datos)"

    # Solo eBird necesita credencial en la fase 1.
    ebird_token: str = ""

    # Límites de cortesía con las APIs públicas. Son organismos que nos regalan
    # los datos: no conviene martillearlos.
    request_timeout: float = 30.0
    max_retries: int = 4
    rate_limit_sleep: float = 0.25

    @property
    def bronze_dir(self) -> Path:
        return self.data_dir / "bronze"

    @property
    def warehouse_path(self) -> Path:
        """Fichero DuckDB donde viven las vistas silver y las tablas gold."""
        return self.data_dir / "appclima.duckdb"

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.bronze_dir):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
