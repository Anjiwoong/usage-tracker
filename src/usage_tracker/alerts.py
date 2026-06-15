from __future__ import annotations

from typing import Callable

from usage_tracker.models import CodexUsage, CursorUsage

NotifyFn = Callable[[str, float, int], None]

ALERT_THRESHOLDS = (80, 90, 100)


class AlertService:
    def __init__(self, notify: NotifyFn | None = None) -> None:
        self._notify = notify or (lambda *_: None)
        self._last_percent: dict[tuple[str, str], float] = {}
        self._initialized: set[tuple[str, str]] = set()

    def _period_key(self, service: str, usage: CursorUsage | CodexUsage) -> str:
        if isinstance(usage, CursorUsage):
            return f"{service}:{usage.billing_cycle_end.isoformat()}"
        return f"{service}:{usage.five_hour_reset_seconds}"

    def _check_metric(
        self,
        service: str,
        percent: float,
        usage: CursorUsage | CodexUsage,
    ) -> None:
        period = self._period_key(service, usage)
        track_key = (service, period)

        if track_key not in self._initialized:
            self._initialized.add(track_key)
            self._last_percent[track_key] = percent
            return

        previous = self._last_percent[track_key]
        for threshold in ALERT_THRESHOLDS:
            if previous < threshold <= percent:
                self._notify(service, percent, threshold)

        self._last_percent[track_key] = percent

    def check(
        self,
        cursor: CursorUsage | None,
        codex: CodexUsage | None,
    ) -> None:
        if cursor and not cursor.error:
            self._check_metric("Cursor", cursor.auto_percent, cursor)
        if codex and not codex.error:
            self._check_metric("Codex", codex.five_hour_used_percent, codex)
