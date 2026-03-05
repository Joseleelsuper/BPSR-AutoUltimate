"""Application configuration.

Loads settings from encrypted secrets (production build) or environment
variables / .env file (development).
"""

from __future__ import annotations

import os
from typing import Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Production builds embed an auto-generated _secrets.py with encrypted values.
# During development that file does not exist yet, so we fall back to env vars.
try:
    from src._secrets import (  # pyright: ignore[reportMissingImports]
        get_api_key as _get_api_key,
        get_server_url as _get_server_url,
    )

    _SECRETS_AVAILABLE = True
except ImportError:
    _SECRETS_AVAILABLE = False


class Config:
    """Centralized configuration for the BPSR client."""

    _instance: Optional["Config"] = None

    def __init__(self) -> None:
        if _SECRETS_AVAILABLE:
            # Encrypted production build — values are decrypted at runtime
            self.server_url: str = _get_server_url()  # pyright: ignore[reportPossiblyUnboundVariable]
            self.api_key: str = _get_api_key()  # pyright: ignore[reportPossiblyUnboundVariable]
        else:
            # Development fallback — configure via .env or environment variables.
            # No default values here: hardcoded secrets would end up in the
            # compiled bytecode even if this branch never executes at runtime.
            self.server_url = os.getenv(
                "BPSR_SERVER_URL", "ws://localhost:4061/bpsr/ws"
            )
            self.api_key = os.getenv("X-API-KEY", "")

        self.reconnect_delay: float = float(os.getenv("BPSR_RECONNECT_DELAY", "3.0"))
        self.max_reconnect_delay: float = float(
            os.getenv("BPSR_MAX_RECONNECT_DELAY", "30.0")
        )
        self.app_title: str = "BPSR AutoUltimate"
        self.app_geometry: str = "800x550"
        self.theme: str = os.getenv("BPSR_THEME", "dark-blue")

    @classmethod
    def instance(cls) -> "Config":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


CONFIG = Config.instance()
