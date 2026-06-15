from __future__ import annotations

from datetime import datetime, timezone

import httpx

from usage_tracker.models import CursorUsage

CURSOR_USAGE_URL = "https://cursor.com/api/usage-summary"

CURSOR_MEMBERSHIP_LABELS = {
    "free": "Free",
    "pro": "Pro",
    "pro_plus": "Pro+",
    "business": "Business",
    "enterprise": "Enterprise",
    "ultra": "Ultra",
}


def format_membership_label(membership_type: str | None) -> str:
    if not membership_type:
        return "Cursor"
    return CURSOR_MEMBERSHIP_LABELS.get(
        membership_type,
        membership_type.replace("_", " ").title(),
    )


def parse_cursor_response(data: dict) -> CursorUsage:
    plan = data["individualUsage"]["plan"]
    billing_end = datetime.fromisoformat(
        data["billingCycleEnd"].replace("Z", "+00:00")
    )
    return CursorUsage(
        auto_percent=float(plan["autoPercentUsed"]),
        api_percent=float(plan["apiPercentUsed"]),
        billing_cycle_end=billing_end,
        fetched_at=datetime.now(timezone.utc),
        membership_type=data.get("membershipType"),
    )


class CursorFetcher:
    def __init__(self, session_token: str) -> None:
        self._session_token = session_token

    def fetch(self) -> CursorUsage:
        now = datetime.now(timezone.utc)
        if not self._session_token:
            return CursorUsage(
                auto_percent=0,
                api_percent=0,
                billing_cycle_end=now,
                fetched_at=now,
                error="CURSOR_SESSION_TOKEN이 설정되지 않았습니다",
            )

        headers = {
            "Cookie": f"WorkosCursorSessionToken={self._session_token}",
            "Origin": "https://cursor.com",
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(CURSOR_USAGE_URL, headers=headers)
                response.raise_for_status()
                return parse_cursor_response(response.json())
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response else "unknown"
            return CursorUsage(
                auto_percent=0,
                api_percent=0,
                billing_cycle_end=now,
                fetched_at=now,
                error=f"Cursor 세션 만료 또는 인증 오류 ({status})",
            )
        except Exception as exc:  # noqa: BLE001
            return CursorUsage(
                auto_percent=0,
                api_percent=0,
                billing_cycle_end=now,
                fetched_at=now,
                error=f"Cursor 조회 실패: {exc}",
            )
