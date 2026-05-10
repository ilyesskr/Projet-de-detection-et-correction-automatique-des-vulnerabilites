"""Application configuration loaded from environment / .env file.

The Settings object is the single source of truth for every external value the
backend needs (database URL, Wazuh/AWX endpoints, JWT secret, ...). It is
cached with ``lru_cache`` so we instantiate it exactly once per process.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the .env path relative to this file so it is found regardless of the
# current working directory (uvicorn from backend/, pytest from project root,
# alembic from anywhere — all work).
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_PROJECT_ROOT = _BACKEND_ROOT.parent
ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App -----------------------------------------------------------
    app_name: str = "PA Platform"
    app_env: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"

    # --- CORS ----------------------------------------------------------
    # Comma-separated origins; parsed by ``cors_origins_list``.
    cors_allow_origins: str = ""

    # --- Database ------------------------------------------------------
    database_url: str

    # --- Redis ---------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # --- Wazuh API -----------------------------------------------------
    wazuh_api_url: str
    wazuh_api_user: str
    wazuh_api_password: str
    wazuh_verify_tls: bool = False
    # Wazuh 4.8+ stores vulnerability inventory in the Wazuh Indexer
    # (OpenSearch), while the Manager API remains the source for agents and
    # health. In the lab the indexer usually listens only on 127.0.0.1, so this
    # can point to an SSH tunnel such as https://127.0.0.1:19200.
    wazuh_indexer_url: str | None = None
    wazuh_indexer_user: str | None = None
    wazuh_indexer_password: str | None = None
    wazuh_indexer_verify_tls: bool = False

    # --- AWX API -------------------------------------------------------
    awx_api_url: str
    awx_api_user: str | None = None
    awx_api_password: str | None = None
    # If set, the AWX client uses bearer-token auth instead of basic auth.
    awx_api_token: str | None = None
    awx_verify_tls: bool = False

    # --- AWX job-template policy --------------------------------------
    # One AWX template id per semantic remediation action. The remediation
    # service maps an incoming action to the corresponding template; if a
    # template is unset, jobs for that action are rejected at create time.
    # Each value must be the numeric id of a real, *approved* AWX job
    # template — never an ad-hoc one — to keep the platform's only-approved-
    # templates rule enforceable.
    awx_template_package_update:  int | None = None
    awx_template_windows_update:  int | None = None
    awx_template_service_restart: int | None = None
    awx_template_config_change:   int | None = None

    # --- JWT (user auth) ----------------------------------------------
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    @field_validator("wazuh_api_url", "wazuh_indexer_url", "awx_api_url")
    @classmethod
    def _strip_trailing_slash(cls, v: str | None) -> str | None:
        return v.rstrip("/") if v else v

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_allow_origins:
            return []
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide Settings singleton."""
    return Settings()
