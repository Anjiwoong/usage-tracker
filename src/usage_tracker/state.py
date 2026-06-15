from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from usage_tracker.models import AppSnapshot, ClaudeUsage, CodexUsage, CursorUsage, StatusLevel

STATUS_EMOJI = {
    StatusLevel.GREEN: "🟢",
    StatusLevel.YELLOW: "🟡",
    StatusLevel.RED: "🔴",
}

STALE_AFTER = timedelta(minutes=5)


@dataclass(frozen=True)
class MenubarEntry:
    service: str
    label: str
    status: StatusLevel


class StateStore:
    def __init__(self) -> None:
        self._cursor: CursorUsage | None = None
        self._codex: CodexUsage | None = None
        self._claude: ClaudeUsage | None = None

    def update(
        self,
        cursor: CursorUsage | None = None,
        codex: CodexUsage | None = None,
        claude: ClaudeUsage | None = None,
    ) -> None:
        if cursor is not None:
            if cursor.error is None or self._cursor is None:
                self._cursor = cursor
            else:
                self._cursor = CursorUsage(
                    auto_percent=self._cursor.auto_percent,
                    api_percent=self._cursor.api_percent,
                    billing_cycle_end=self._cursor.billing_cycle_end,
                    fetched_at=cursor.fetched_at,
                    membership_type=self._cursor.membership_type,
                    error=cursor.error,
                )
        if codex is not None:
            if codex.error is None or self._codex is None:
                self._codex = codex
            else:
                self._codex = CodexUsage(
                    five_hour_used_percent=self._codex.five_hour_used_percent,
                    five_hour_reset_seconds=self._codex.five_hour_reset_seconds,
                    seven_day_used_percent=self._codex.seven_day_used_percent,
                    seven_day_reset_seconds=self._codex.seven_day_reset_seconds,
                    fetched_at=codex.fetched_at,
                    plan_type=self._codex.plan_type,
                    error=codex.error,
                )
        if claude is not None:
            if claude.error is None or self._claude is None:
                self._claude = claude
            else:
                self._claude = ClaudeUsage(
                    five_hour_used_percent=self._claude.five_hour_used_percent,
                    five_hour_reset_seconds=self._claude.five_hour_reset_seconds,
                    seven_day_used_percent=self._claude.seven_day_used_percent,
                    seven_day_reset_seconds=self._claude.seven_day_reset_seconds,
                    fetched_at=claude.fetched_at,
                    error=claude.error,
                )

    def snapshot(self) -> AppSnapshot:
        return AppSnapshot(cursor=self._cursor, codex=self._codex, claude=self._claude)

    def _cursor_display(self) -> str:
        if self._cursor is None or self._cursor.error:
            return "?"
        return f"{self._cursor.auto_percent:.0f}"

    def _codex_display(self) -> str:
        if self._codex is None or self._codex.error:
            return "?"
        return f"{self._codex.five_hour_used_percent:.0f}"

    def _claude_display(self) -> str:
        if self._claude is None or self._claude.error:
            return "?"
        return f"{self._claude.five_hour_used_percent:.0f}"

    def menubar_cursor_label(self) -> str:
        return self._cursor_display()

    def menubar_codex_label(self) -> str:
        return self._codex_display()

    def menubar_claude_label(self) -> str:
        return self._claude_display()

    def menubar_entries(self) -> list[MenubarEntry]:
        entries: list[MenubarEntry] = []
        if self._cursor and not self._cursor.error:
            entries.append(
                MenubarEntry(
                    "cursor",
                    f"{self._cursor.auto_percent:.0f}",
                    StatusLevel.from_percent(self._cursor.auto_percent),
                )
            )
        if self._codex and not self._codex.error:
            entries.append(
                MenubarEntry(
                    "codex",
                    f"{self._codex.five_hour_used_percent:.0f}",
                    StatusLevel.from_percent(self._codex.five_hour_used_percent),
                )
            )
        if self._claude and not self._claude.error:
            entries.append(
                MenubarEntry(
                    "claude",
                    f"{self._claude.five_hour_used_percent:.0f}",
                    StatusLevel.from_percent(self._claude.five_hour_used_percent),
                )
            )
        return entries

    def has_menubar_entries(self) -> bool:
        return bool(self.menubar_entries())

    def is_unavailable(self) -> bool:
        return not self.has_menubar_entries()

    def menubar_title_fallback(self) -> str:
        entries = self.menubar_entries()
        if not entries:
            return "⚠ —"
        parts = [
            f"{STATUS_EMOJI[entry.status]} {entry.label}%"
            for entry in entries
        ]
        return "  ·  ".join(parts)

    def menubar_title(self) -> str:
        return self.menubar_title_fallback()

    def cursor_status_level(self) -> StatusLevel:
        if self._cursor is None or self._cursor.error:
            return StatusLevel.YELLOW
        return StatusLevel.from_percent(self._cursor.auto_percent)

    def codex_status_level(self) -> StatusLevel:
        if self._codex is None or self._codex.error:
            return StatusLevel.YELLOW
        return StatusLevel.from_percent(self._codex.five_hour_used_percent)

    def claude_status_level(self) -> StatusLevel:
        if self._claude is None or self._claude.error:
            return StatusLevel.YELLOW
        return StatusLevel.from_percent(self._claude.five_hour_used_percent)

    def status_level(self) -> StatusLevel:
        percents: list[float] = []
        if self._cursor and not self._cursor.error:
            percents.append(self._cursor.auto_percent)
        if self._codex and not self._codex.error:
            percents.append(self._codex.five_hour_used_percent)
        if self._claude and not self._claude.error:
            percents.append(self._claude.five_hour_used_percent)
        if not percents:
            return StatusLevel.YELLOW
        return StatusLevel.from_percent(max(percents))

    def is_stale(self) -> bool:
        now = datetime.now(timezone.utc)
        for usage in (self._cursor, self._codex, self._claude):
            if usage and not usage.error:
                if now - usage.fetched_at > STALE_AFTER:
                    return True
        return False
