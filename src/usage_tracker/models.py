from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class StatusLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

    @classmethod
    def from_percent(cls, percent: float) -> StatusLevel:
        if percent < 50:
            return cls.GREEN
        if percent < 80:
            return cls.YELLOW
        return cls.RED


@dataclass
class CursorUsage:
    auto_percent: float
    api_percent: float
    billing_cycle_end: datetime
    fetched_at: datetime
    membership_type: str | None = None
    error: str | None = None


@dataclass
class CodexUsage:
    five_hour_used_percent: float
    five_hour_reset_seconds: int
    seven_day_used_percent: float
    seven_day_reset_seconds: int
    fetched_at: datetime
    plan_type: str | None = None
    error: str | None = None


@dataclass
class AppSnapshot:
    cursor: CursorUsage | None = None
    codex: CodexUsage | None = None
