from usage_tracker.config import load_config


def test_load_config_from_env(monkeypatch):
    monkeypatch.setenv("CURSOR_SESSION_TOKEN", "test-token")
    monkeypatch.setenv("POLL_INTERVAL_SECONDS", "30")
    monkeypatch.setenv("ALERT_THRESHOLD_WARN", "75")
    monkeypatch.setenv("ALERT_THRESHOLD_CRITICAL", "85")
    config = load_config()

    assert config.cursor_session_token == "test-token"
    assert config.poll_interval_seconds == 30
    assert config.alert_threshold_warn == 75
    assert config.alert_threshold_critical == 85


def test_load_config_defaults(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("usage_tracker.config.load_dotenv", lambda *_a, **_k: True)
    for key in (
        "CURSOR_SESSION_TOKEN",
        "POLL_INTERVAL_SECONDS",
        "ALERT_THRESHOLD_WARN",
        "ALERT_THRESHOLD_CRITICAL",
    ):
        monkeypatch.delenv(key, raising=False)
    config = load_config()

    assert config.cursor_session_token == ""
    assert config.poll_interval_seconds == 60
    assert config.alert_threshold_warn == 80
    assert config.alert_threshold_critical == 90
