import json
from pathlib import Path

import httpx

from usage_tracker.claude_fetcher import ClaudeFetcher, load_access_token, parse_claude_usage

FIXTURE = Path(__file__).parent / "fixtures" / "claude_usage.json"


def test_parse_claude_usage():
    data = json.loads(FIXTURE.read_text())
    usage = parse_claude_usage(data)

    assert usage.five_hour_used_percent == 23.5
    assert usage.five_hour_reset_seconds > 0
    assert usage.seven_day_used_percent == 41.2
    assert usage.seven_day_reset_seconds > 0
    assert usage.error is None


def test_load_access_token_from_default_path(monkeypatch, tmp_path):
    credentials = tmp_path / ".credentials.json"
    credentials.write_text(
        json.dumps({"claudeAiOauth": {"accessToken": "test-token"}})
    )
    monkeypatch.setattr(
        "usage_tracker.claude_fetcher.DEFAULT_CREDENTIALS_PATH",
        credentials,
    )

    assert load_access_token() == "test-token"


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
            assert headers["Authorization"] == "Bearer test-token"
            assert headers["anthropic-beta"] == "oauth-2025-04-20"
            return MockResponse()

    monkeypatch.setattr(httpx, "Client", MockClient)
    monkeypatch.setattr(
        "usage_tracker.claude_fetcher.load_access_token",
        lambda: "test-token",
    )
    usage = ClaudeFetcher().fetch()

    assert usage.five_hour_used_percent == 23.5
    assert usage.error is None


def test_fetch_missing_credentials(monkeypatch):
    monkeypatch.setattr("usage_tracker.claude_fetcher.load_access_token", lambda: None)
    usage = ClaudeFetcher().fetch()
    assert usage.error is not None
    assert "claude login" in usage.error


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
    monkeypatch.setattr(
        "usage_tracker.claude_fetcher.load_access_token",
        lambda: "bad-token",
    )
    usage = ClaudeFetcher().fetch()

    assert usage.error is not None
    assert "401" in usage.error
