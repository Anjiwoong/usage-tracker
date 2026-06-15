from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from usage_tracker.models import ClaudeUsage

CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
DEFAULT_CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"


def load_access_token() -> str | None:
    if not DEFAULT_CREDENTIALS_PATH.is_file():
        return None

    try:
        data = json.loads(DEFAULT_CREDENTIALS_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return None

    oauth = data.get("claudeAiOauth") or data.get("claude_ai_oauth") or {}
    token = oauth.get("accessToken") or oauth.get("access_token")
    return token if isinstance(token, str) and token else None


def _reset_seconds(resets_at: str | None, now: datetime) -> int:
    if not resets_at:
        return 0
    reset_dt = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
    if reset_dt.tzinfo is None:
        reset_dt = reset_dt.replace(tzinfo=timezone.utc)
    return max(0, int((reset_dt - now).total_seconds()))


def _bucket_utilization(bucket: dict | None) -> float:
    if not bucket:
        return 0.0
    if "utilization" in bucket:
        return float(bucket["utilization"])
    if "used_percentage" in bucket:
        return float(bucket["used_percentage"])
    return 0.0


def parse_claude_usage(data: dict) -> ClaudeUsage:
    now = datetime.now(timezone.utc)
    five_hour = data.get("five_hour")
    seven_day = data.get("seven_day")

    return ClaudeUsage(
        five_hour_used_percent=_bucket_utilization(five_hour),
        five_hour_reset_seconds=_reset_seconds(
            five_hour.get("resets_at") if five_hour else None,
            now,
        ),
        seven_day_used_percent=_bucket_utilization(seven_day),
        seven_day_reset_seconds=_reset_seconds(
            seven_day.get("resets_at") if seven_day else None,
            now,
        ),
        fetched_at=now,
    )


class ClaudeFetcher:
    def fetch(self) -> ClaudeUsage:
        now = datetime.now(timezone.utc)
        token = load_access_token()
        if not token:
            return ClaudeUsage(
                five_hour_used_percent=0,
                five_hour_reset_seconds=0,
                seven_day_used_percent=0,
                seven_day_reset_seconds=0,
                fetched_at=now,
                error="Claude Code 로그인 필요: `claude login` 실행",
            )

        headers = {
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(CLAUDE_USAGE_URL, headers=headers)
                response.raise_for_status()
                return parse_claude_usage(response.json())
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response else "unknown"
            return ClaudeUsage(
                five_hour_used_percent=0,
                five_hour_reset_seconds=0,
                seven_day_used_percent=0,
                seven_day_reset_seconds=0,
                fetched_at=now,
                error=f"Claude 인증 만료 또는 조회 오류 ({status})",
            )
        except Exception as exc:  # noqa: BLE001
            return ClaudeUsage(
                five_hour_used_percent=0,
                five_hour_reset_seconds=0,
                seven_day_used_percent=0,
                seven_day_reset_seconds=0,
                fetched_at=now,
                error=f"Claude 조회 실패: {exc}",
            )
