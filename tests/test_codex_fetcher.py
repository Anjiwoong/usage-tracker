import json
from pathlib import Path

from usage_tracker.codex_fetcher import CodexFetcher, parse_codex_rate_limits

FIXTURE = Path(__file__).parent / "fixtures" / "codex_rate_limits.json"


def test_parse_codex_rate_limits():
    data = json.loads(FIXTURE.read_text())
    usage = parse_codex_rate_limits(data)

    assert usage.five_hour_used_percent == 52.0
    assert usage.five_hour_reset_seconds > 0
    assert usage.seven_day_used_percent == 41.0
    assert usage.seven_day_reset_seconds > 0
    assert usage.error is None


def test_fetch_via_mocked_subprocess(monkeypatch):
    fixture_result = json.loads(FIXTURE.read_text())

    class FakeProcess:
        def __init__(self):
            self._responses = iter([
                '{"id":1,"result":{"userAgent":"test"}}\n',
                '{"method":"remoteControl/status/changed","params":{}}\n',
                json.dumps({"id": 2, "result": fixture_result}) + "\n",
            ])

        def poll(self):
            return None

        def terminate(self):
            pass

        def wait(self, timeout=None):
            return 0

        @property
        def stdin(self):
            return self

        @property
        def stdout(self):
            return self

        def write(self, data):
            pass

        def flush(self):
            pass

        def readline(self):
            return next(self._responses)

    monkeypatch.setattr(
        "usage_tracker.codex_fetcher.subprocess.Popen",
        lambda *args, **kwargs: FakeProcess(),
    )
    monkeypatch.setattr(
        "usage_tracker.codex_fetcher._read_json_response",
        lambda proc, request_id, timeout=15.0: (
            {"id": 1, "result": {}}
            if request_id == 1
            else {"id": 2, "result": fixture_result}
        ),
    )

    usage = CodexFetcher().fetch()
    assert usage.five_hour_used_percent == 52.0
    assert usage.error is None
