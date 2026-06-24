"""
Configuration for odoo-mcp-server.

All settings are loaded from environment variables (or a .env file in
development). Pydantic validates types and required fields at startup,
so any misconfiguration crashes the program with a clear error before
any business logic runs.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Server configuration loaded from environment variables or `.env`.

    Every field below maps to an env var of the same name (uppercase).
    Required fields have no default and will crash at startup if missing.
    Optional fields use the default specified in `Field(...)`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Odoo connection ----
    odoo_url: str = Field(
        description="Base URL of the Odoo instance (no trailing slash)."
    )
    odoo_db: str = Field(
        description="Odoo database name."
    )
    odoo_username: str = Field(
        description="Service-account username (email) used to authenticate."
    )
    odoo_api_key: str = Field(
        description="Service-account API key. Treat as a secret."
    )

    # ---- MCP security ----
    mcp_permission_mode: Literal["read", "write"] = Field(
        default="read",
        description="'read' is the safe default. 'write' must be opted into explicitly.",
    )
    mcp_max_records: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Hard cap on records returned per tool call.",
    )
    mcp_query_timeout: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Timeout in seconds for any single Odoo query.",
    )
    mcp_rate_limit: int = Field(
        default=60,
        ge=1,
        description="Maximum tool calls per minute, per client.",
    )
    mcp_audit_path: str = Field(
        default="./logs/audit.log",
        description="Path to the append-only audit log.",
    )

    # ---- Logging ----
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Standard Python logging level.",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Return a single, cached Settings instance.

    The first call reads `.env` and validates every field; later calls
    return the cached object. We always use `get_settings()` instead
    of calling `Settings()` directly so the validation only happens once.
    """
    return Settings()