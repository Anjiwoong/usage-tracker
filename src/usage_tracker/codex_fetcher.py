from __future__ import annotations

import json
import select
import subprocess
import time
from datetime import datetime, timezone

from usage_tracker.models import CodexUsage


def parse_codex_rate_limits(data: dict) -> CodexUsage:
    rate_limits = data.get("rateLimits", data)
    primary = rate_limits["primary"]
    secondary = rate_limits.get("secondary")

    now = time.time()

    def reset_seconds(bucket: dict | None) -> int:
        if not bucket:
            return 0
        resets_at = bucket.get("resetsAt", 0)
        return max(0, int(resets_at - now))

    return CodexUsage(
        five_hour_used_percent=float(primary["usedPercent"]),
        five_hour_reset_seconds=reset_seconds(primary),
        seven_day_used_percent=float(secondary["usedPercent"]) if secondary else 0.0,
        seven_day_reset_seconds=reset_seconds(secondary),
        fetched_at=datetime.now(timezone.utc),
    )


def _read_json_response(proc: subprocess.Popen[str], request_id: int, timeout: float = 15.0) -> dict:
    assert proc.stdout is not None
    deadline = time.time() + timeout
    while time.time() < deadline:
        remaining = deadline - time.time()
        ready, _, _ = select.select([proc.stdout], [], [], max(0.1, remaining))
        if not ready:
            break
        line = proc.stdout.readline()
        if not line:
            break
        payload = json.loads(line)
        if payload.get("id") == request_id:
            return payload
    raise TimeoutError(f"Codex app-server 응답 없음 (id={request_id})")


class CodexFetcher:
    def fetch(self) -> CodexUsage:
        now = datetime.now(timezone.utc)
        try:
            proc = subprocess.Popen(
                ["codex", "app-server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            assert proc.stdin is not None

            init_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"clientInfo": {"name": "usage-tracker", "version": "0.1.0"}},
            }
            proc.stdin.write(json.dumps(init_msg) + "\n")
            proc.stdin.flush()
            _read_json_response(proc, request_id=1)

            limits_msg = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "account/rateLimits/read",
                "params": {},
            }
            proc.stdin.write(json.dumps(limits_msg) + "\n")
            proc.stdin.flush()
            payload = _read_json_response(proc, request_id=2)
            proc.terminate()
            proc.wait(timeout=5)

            if "error" in payload:
                return CodexUsage(
                    five_hour_used_percent=0,
                    five_hour_reset_seconds=0,
                    seven_day_used_percent=0,
                    seven_day_reset_seconds=0,
                    fetched_at=now,
                    error=f"Codex 인증 필요: {payload['error']}",
                )

            return parse_codex_rate_limits(payload["result"])
        except FileNotFoundError:
            return CodexUsage(
                five_hour_used_percent=0,
                five_hour_reset_seconds=0,
                seven_day_used_percent=0,
                seven_day_reset_seconds=0,
                fetched_at=now,
                error="codex CLI가 설치되지 않았습니다",
            )
        except Exception as exc:  # noqa: BLE001
            return CodexUsage(
                five_hour_used_percent=0,
                five_hour_reset_seconds=0,
                seven_day_used_percent=0,
                seven_day_reset_seconds=0,
                fetched_at=now,
                error=f"Codex 조회 실패: {exc}",
            )
