from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class Config:
    cursor_session_token: str
    poll_interval_seconds: int
    alert_threshold_warn: int
    alert_threshold_critical: int


def load_config() -> Config:
    load_dotenv(PROJECT_ROOT / ".env")
    return Config(
        cursor_session_token=os.getenv("CURSOR_SESSION_TOKEN", ""),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "60")),
        alert_threshold_warn=int(os.getenv("ALERT_THRESHOLD_WARN", "80")),
        alert_threshold_critical=int(os.getenv("ALERT_THRESHOLD_CRITICAL", "90")),
    )
