from datetime import datetime, timezone

from usage_tracker.models import CursorUsage, StatusLevel


def test_status_level_from_percent():
    assert StatusLevel.from_percent(30) == StatusLevel.GREEN
    assert StatusLevel.from_percent(50) == StatusLevel.YELLOW
    assert StatusLevel.from_percent(79) == StatusLevel.YELLOW
    assert StatusLevel.from_percent(80) == StatusLevel.RED


def test_cursor_usage_defaults():
    usage = CursorUsage(
        auto_percent=38.0,
        api_percent=12.0,
        billing_cycle_end=datetime(2026, 5, 2, tzinfo=timezone.utc),
        fetched_at=datetime.now(timezone.utc),
    )
    assert usage.error is None
    assert usage.auto_percent == 38.0
