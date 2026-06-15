from datetime import datetime, timedelta, timezone

from usage_tracker.models import CodexUsage, CursorUsage, StatusLevel
from usage_tracker.state import StateStore


def make_cursor(auto: float = 38.0, api: float = 12.0) -> CursorUsage:
    now = datetime.now(timezone.utc)
    return CursorUsage(
        auto_percent=auto,
        api_percent=api,
        billing_cycle_end=now + timedelta(days=20),
        fetched_at=now,
    )


def make_codex(five: float = 52.0) -> CodexUsage:
    now = datetime.now(timezone.utc)
    return CodexUsage(
        five_hour_used_percent=five,
        five_hour_reset_seconds=12000,
        seven_day_used_percent=41.0,
        seven_day_reset_seconds=345600,
        fetched_at=now,
    )


def test_menubar_title():
    store = StateStore()
    store.update(cursor=make_cursor(), codex=make_codex())
    assert store.menubar_title() == "🟢 38%  ·  🟡 52%"


def test_menubar_title_partial_error():
    store = StateStore()
    cursor = make_cursor()
    cursor.error = "세션 만료"
    store.update(cursor=cursor, codex=make_codex())
    assert store.menubar_title() == "🟡 ?%  ·  🟡 52%"


def test_status_level_uses_worst_default_metric():
    store = StateStore()
    store.update(cursor=make_cursor(auto=30), codex=make_codex(five=85))
    assert store.status_level() == StatusLevel.RED


def test_stale_detection():
    store = StateStore()
    old = make_cursor()
    old.fetched_at = datetime.now(timezone.utc) - timedelta(minutes=6)
    store.update(cursor=old, codex=make_codex())
    assert store.is_stale() is True
