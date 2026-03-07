"""Application configuration for mobile.

Loads settings from environment variables / .env file (development)
or from hardcoded defaults for production Android builds.
"""

from __future__ import annotations

import os
from typing import Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


class Config:
    """Centralized configuration for the BPSR mobile client."""

    _instance: Optional["Config"] = None

    def __init__(self) -> None:
        self.server_url: str = os.getenv(
            "BPSR_SERVER_URL", "ws://localhost:4061/bpsr/ws"
        )
        self.api_key: str = os.getenv("X-API-KEY", "")
        self.reconnect_delay: float = float(os.getenv("BPSR_RECONNECT_DELAY", "3.0"))
        self.max_reconnect_delay: float = float(
            os.getenv("BPSR_MAX_RECONNECT_DELAY", "30.0")
        )

        # Tap positions as screen ratios: key_name → (x_ratio, y_ratio)
        # Reference: (1680, 940) on a 2400×1080 display
        self.tap_positions: dict[str, tuple[float, float]] = {
            "r": (1680 / 2400, 940 / 1080),
        }

    @classmethod
    def instance(cls) -> "Config":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


CONFIG = Config.instance()
