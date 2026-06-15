from datetime import datetime, timezone

from usage_tracker.alerts import AlertService
from usage_tracker.models import CodexUsage, CursorUsage


def test_alert_fires_once_when_crossing_threshold():
    fired: list[tuple[str, int]] = []

    def notify(service: str, percent: float, threshold: int) -> None:
        fired.append((service, threshold))

    alerts = AlertService(notify=notify)
    base = datetime.now(timezone.utc)

    alerts.check(CursorUsage(79, 10, base, base), None)
    assert fired == []

    alerts.check(CursorUsage(81, 10, base, base), None)
    assert fired == [("Cursor", 80)]

    alerts.check(CursorUsage(85, 10, base, base), None)
    assert fired == [("Cursor", 80)]

    alerts.check(CursorUsage(91, 10, base, base), None)
    assert fired == [("Cursor", 80), ("Cursor", 90)]


def test_alert_fires_at_100_percent():
    fired: list[tuple[str, int]] = []

    def notify(service: str, percent: float, threshold: int) -> None:
        fired.append((service, threshold))

    alerts = AlertService(notify=notify)
    base = datetime.now(timezone.utc)

    alerts.check(None, CodexUsage(50, 100, 20, 0, base))
    alerts.check(None, CodexUsage(79, 100, 20, 0, base))
    alerts.check(None, CodexUsage(81, 100, 20, 0, base))
    alerts.check(None, CodexUsage(91, 100, 20, 0, base))
    alerts.check(None, CodexUsage(100, 100, 20, 0, base))

    assert fired == [("Codex", 80), ("Codex", 90), ("Codex", 100)]


def test_alert_resets_on_codex_window_change():
    fired: list[tuple[str, int]] = []

    def notify(service: str, percent: float, threshold: int) -> None:
        fired.append((service, threshold))

    alerts = AlertService(notify=notify)
    base = datetime.now(timezone.utc)

    alerts.check(None, CodexUsage(50, 100, 20, 0, base))
    alerts.check(None, CodexUsage(85, 100, 20, 0, base))
    assert fired == [("Codex", 80)]

    alerts.check(None, CodexUsage(50, 200, 20, 0, base))
    alerts.check(None, CodexUsage(85, 200, 20, 0, base))
    assert fired == [("Codex", 80), ("Codex", 80)]
