import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from usage_tracker.cursor_fetcher import CursorFetcher, format_membership_label, parse_cursor_response

FIXTURE = Path(__file__).parent / "fixtures" / "cursor_usage_summary.json"


def test_format_membership_label():
    assert format_membership_label("pro_plus") == "Pro+"
    assert format_membership_label("pro") == "Pro"
    assert format_membership_label("unknown_tier") == "Unknown Tier"
    assert format_membership_label(None) == "Cursor"


def test_parse_cursor_response():
    data = json.loads(FIXTURE.read_text())
    usage = parse_cursor_response(data)

    assert usage.auto_percent == 38.5
    assert usage.api_percent == 12.0
    assert usage.membership_type == "pro_plus"
    assert usage.billing_cycle_end == datetime(2026, 5, 2, 14, 11, 55, tzinfo=timezone.utc)
    assert usage.error is None


def test_fetch_success(monkeypatch):
    data = json.loads(FIXTURE.read_text())

    class MockResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return data

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None):
            assert "WorkosCursorSessionToken=secret" in headers["Cookie"]
            return MockResponse()

    monkeypatch.setattr(httpx, "Client", MockClient)
    fetcher = CursorFetcher("secret")
    usage = fetcher.fetch()

    assert usage.auto_percent == 38.5
    assert usage.error is None


def test_fetch_auth_error(monkeypatch):
    class MockResponse:
        status_code = 401

        def raise_for_status(self):
            raise httpx.HTTPStatusError("Unauthorized", request=None, response=self)

        def json(self):
            return {}

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, headers=None):
            return MockResponse()

    monkeypatch.setattr(httpx, "Client", MockClient)
    fetcher = CursorFetcher("bad-token")
    usage = fetcher.fetch()

    assert usage.error is not None
    assert "세션" in usage.error or "401" in usage.error
