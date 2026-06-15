# Usage Tracker 구현 계획

> **에이전트 작업자용:** 필수 서브스킬 — `superpowers:subagent-driven-development`(권장) 또는 `superpowers:executing-plans`로 이 계획을 태스크 단위로 구현하세요. 각 단계는 체크박스(`- [ ]`)로 추적합니다.

**목표:** Cursor Pro+와 Codex(ChatGPT Team) 사용량을 macOS 메뉴바에서 실시간에 가깝게 확인하는 개인용 앱을 만든다.

**아키텍처:** Python + rumps 메뉴바 앱. 60초마다 Cursor(HTTP, 비공식 API)와 Codex(로컬 JSON-RPC)를 병렬 폴링하고, StateStore가 메뉴바 제목·색상·알림을 계산한다. 클릭 시 상세 breakdown을 메뉴/팝오버로 표시한다.

**기술 스택:** Python 3.11+, rumps, httpx, python-dotenv, pytest

**설계 스펙:** `docs/superpowers/specs/2026-06-12-usage-tracker-design.md`

---

## 파일 구조

| 파일 | 책임 |
|------|------|
| `pyproject.toml` | 의존성, 패키지 메타데이터, CLI 진입점 |
| `.env.example` | 설정 템플릿 |
| `.gitignore` | `.env`, `__pycache__`, `.venv` 제외 |
| `src/usage_tracker/models.py` | `CursorUsage`, `CodexUsage`, `AppSnapshot` 데이터 클래스 |
| `src/usage_tracker/config.py` | `.env` 로드 |
| `src/usage_tracker/cursor_fetcher.py` | Cursor usage-summary 파싱 |
| `src/usage_tracker/codex_fetcher.py` | Codex app-server JSON-RPC |
| `src/usage_tracker/state.py` | 메뉴바 제목, 색상, stale 판단 |
| `src/usage_tracker/alerts.py` | 80%/90% 임계치 알림 + 중복 방지 |
| `src/usage_tracker/popover.py` | 상세 breakdown 텍스트 생성 |
| `src/usage_tracker/main.py` | rumps 앱, 폴링, 메뉴 |
| `tests/fixtures/` | API 응답 JSON 픽스처 |
| `tests/test_*.py` | 단위 테스트 |

---

### Task 1: 프로젝트 스캐폴딩

**파일:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/usage_tracker/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: git 초기화 및 디렉터리 생성**

```bash
cd /Users/austin/Desktop/usage-tracker
git init
mkdir -p src/usage_tracker tests/fixtures
touch src/usage_tracker/__init__.py tests/__init__.py
```

- [ ] **Step 2: pyproject.toml 작성**

```toml
[project]
name = "usage-tracker"
version = "0.1.0"
description = "macOS menubar app for Cursor and Codex usage"
requires-python = ">=3.11"
dependencies = [
    "rumps>=0.4.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0"]

[project.scripts]
usage-tracker = "usage_tracker.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/usage_tracker"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 3: .gitignore 작성**

```
.env
.venv/
__pycache__/
*.pyc
.pytest_cache/
dist/
*.egg-info/
.DS_Store
```

- [ ] **Step 4: .env.example 작성**

```env
CURSOR_SESSION_TOKEN=
POLL_INTERVAL_SECONDS=60
ALERT_THRESHOLD_WARN=80
ALERT_THRESHOLD_CRITICAL=90
```

- [ ] **Step 5: 가상환경 생성 및 설치**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: 설치 오류 없음

- [ ] **Step 6: 커밋**

```bash
git add pyproject.toml .gitignore .env.example src/ tests
git commit -m "chore: 프로젝트 스캐폴딩 추가"
```

---

### Task 2: 데이터 모델

**파일:**
- Create: `src/usage_tracker/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_models.py`:

```python
from datetime import datetime, timezone

from usage_tracker.models import CursorUsage, CodexUsage, StatusLevel


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
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError` 또는 `StatusLevel` 미정의

- [ ] **Step 3: models.py 구현**

`src/usage_tracker/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class StatusLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

    @classmethod
    def from_percent(cls, percent: float) -> StatusLevel:
        if percent < 50:
            return cls.GREEN
        if percent < 80:
            return cls.YELLOW
        return cls.RED


@dataclass
class CursorUsage:
    auto_percent: float
    api_percent: float
    billing_cycle_end: datetime
    fetched_at: datetime
    error: str | None = None


@dataclass
class CodexUsage:
    five_hour_used_percent: float
    five_hour_reset_seconds: int
    seven_day_used_percent: float
    seven_day_reset_seconds: int
    fetched_at: datetime
    error: str | None = None


@dataclass
class AppSnapshot:
    cursor: CursorUsage | None = None
    codex: CodexUsage | None = None
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_models.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 5: 커밋**

```bash
git add src/usage_tracker/models.py tests/test_models.py
git commit -m "feat: 사용량 데이터 모델 추가"
```

---

### Task 3: 설정 로더

**파일:**
- Create: `src/usage_tracker/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_config.py`:

```python
import os
from pathlib import Path

from usage_tracker.config import load_config


def test_load_config_from_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CURSOR_SESSION_TOKEN=test-token\n"
        "POLL_INTERVAL_SECONDS=30\n"
        "ALERT_THRESHOLD_WARN=75\n"
        "ALERT_THRESHOLD_CRITICAL=85\n"
    )
    monkeypatch.chdir(tmp_path)
    config = load_config()

    assert config.cursor_session_token == "test-token"
    assert config.poll_interval_seconds == 30
    assert config.alert_threshold_warn == 75
    assert config.alert_threshold_critical == 85


def test_load_config_defaults(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CURSOR_SESSION_TOKEN", raising=False)
    config = load_config()

    assert config.cursor_session_token == ""
    assert config.poll_interval_seconds == 60
    assert config.alert_threshold_warn == 80
    assert config.alert_threshold_critical == 90
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_config.py -v
```

Expected: FAIL

- [ ] **Step 3: config.py 구현**

`src/usage_tracker/config.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    cursor_session_token: str
    poll_interval_seconds: int
    alert_threshold_warn: int
    alert_threshold_critical: int


def load_config() -> Config:
    load_dotenv()
    return Config(
        cursor_session_token=os.getenv("CURSOR_SESSION_TOKEN", ""),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "60")),
        alert_threshold_warn=int(os.getenv("ALERT_THRESHOLD_WARN", "80")),
        alert_threshold_critical=int(os.getenv("ALERT_THRESHOLD_CRITICAL", "90")),
    )
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_config.py -v
```

Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/usage_tracker/config.py tests/test_config.py
git commit -m "feat: .env 기반 설정 로더 추가"
```

---

### Task 4: CursorFetcher

**파일:**
- Create: `src/usage_tracker/cursor_fetcher.py`
- Create: `tests/fixtures/cursor_usage_summary.json`
- Create: `tests/test_cursor_fetcher.py`

- [ ] **Step 1: 픽스처 JSON 작성**

`tests/fixtures/cursor_usage_summary.json`:

```json
{
  "billingCycleStart": "2026-04-02T14:11:55.000Z",
  "billingCycleEnd": "2026-05-02T14:11:55.000Z",
  "membershipType": "pro_plus",
  "individualUsage": {
    "plan": {
      "autoPercentUsed": 38.5,
      "apiPercentUsed": 12.0
    }
  }
}
```

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_cursor_fetcher.py`:

```python
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from usage_tracker.cursor_fetcher import CursorFetcher, parse_cursor_response


FIXTURE = Path(__file__).parent / "fixtures" / "cursor_usage_summary.json"


def test_parse_cursor_response():
    data = json.loads(FIXTURE.read_text())
    usage = parse_cursor_response(data)

    assert usage.auto_percent == 38.5
    assert usage.api_percent == 12.0
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
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_cursor_fetcher.py -v
```

Expected: FAIL

- [ ] **Step 4: cursor_fetcher.py 구현**

`src/usage_tracker/cursor_fetcher.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from usage_tracker.models import CursorUsage

CURSOR_USAGE_URL = "https://cursor.com/api/usage-summary"


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
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_cursor_fetcher.py -v
```

Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add src/usage_tracker/cursor_fetcher.py tests/fixtures/cursor_usage_summary.json tests/test_cursor_fetcher.py
git commit -m "feat: Cursor usage-summary fetcher 추가"
```

---

### Task 5: CodexFetcher

**파일:**
- Create: `src/usage_tracker/codex_fetcher.py`
- Create: `tests/fixtures/codex_rate_limits.json`
- Create: `tests/test_codex_fetcher.py`

- [ ] **Step 1: 픽스처 JSON 작성**

`tests/fixtures/codex_rate_limits.json`:

```json
{
  "five_hour": {
    "usedPercent": 52.0,
    "resetAfterSeconds": 12000
  },
  "seven_day": {
    "usedPercent": 41.0,
    "resetAfterSeconds": 345600
  }
}
```

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_codex_fetcher.py`:

```python
import json
from pathlib import Path

from usage_tracker.codex_fetcher import CodexFetcher, parse_codex_rate_limits

FIXTURE = Path(__file__).parent / "fixtures" / "codex_rate_limits.json"


def test_parse_codex_rate_limits():
    data = json.loads(FIXTURE.read_text())
    usage = parse_codex_rate_limits(data)

    assert usage.five_hour_used_percent == 52.0
    assert usage.five_hour_reset_seconds == 12000
    assert usage.seven_day_used_percent == 41.0
    assert usage.seven_day_reset_seconds == 345600
    assert usage.error is None


def test_fetch_via_mocked_subprocess(monkeypatch):
    fixture = json.loads(FIXTURE.read_text())

    class FakeProcess:
        def __init__(self):
            self._responses = iter([
                '{"jsonrpc":"2.0","id":1,"result":{"capabilities":{}}}\n',
                json.dumps({"jsonrpc": "2.0", "id": 2, "result": fixture}) + "\n",
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

    usage = CodexFetcher().fetch()
    assert usage.five_hour_used_percent == 52.0
    assert usage.error is None
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_codex_fetcher.py -v
```

Expected: FAIL

- [ ] **Step 4: codex_fetcher.py 구현**

`src/usage_tracker/codex_fetcher.py`:

```python
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone

from usage_tracker.models import CodexUsage


def parse_codex_rate_limits(data: dict) -> CodexUsage:
    five = data["five_hour"]
    seven = data["seven_day"]
    return CodexUsage(
        five_hour_used_percent=float(five["usedPercent"]),
        five_hour_reset_seconds=int(five["resetAfterSeconds"]),
        seven_day_used_percent=float(seven["usedPercent"]),
        seven_day_reset_seconds=int(seven["resetAfterSeconds"]),
        fetched_at=datetime.now(timezone.utc),
    )


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
            assert proc.stdout is not None

            init_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"clientInfo": {"name": "usage-tracker", "version": "0.1.0"}},
            }
            proc.stdin.write(json.dumps(init_msg) + "\n")
            proc.stdin.flush()
            proc.stdout.readline()

            limits_msg = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "account/rateLimits/read",
                "params": {},
            }
            proc.stdin.write(json.dumps(limits_msg) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            proc.terminate()
            proc.wait(timeout=5)

            payload = json.loads(line)
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
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_codex_fetcher.py -v
```

Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add src/usage_tracker/codex_fetcher.py tests/fixtures/codex_rate_limits.json tests/test_codex_fetcher.py
git commit -m "feat: Codex rateLimits fetcher 추가"
```

---

### Task 6: StateStore

**파일:**
- Create: `src/usage_tracker/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_state.py`:

```python
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
    assert store.menubar_title() == "C 38% · X 52%"


def test_menubar_title_partial_error():
    store = StateStore()
    cursor = make_cursor()
    cursor.error = "세션 만료"
    store.update(cursor=cursor, codex=make_codex())
    assert store.menubar_title() == "C ? · X 52%"


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
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_state.py -v
```

Expected: FAIL

- [ ] **Step 3: state.py 구현**

`src/usage_tracker/state.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from usage_tracker.models import AppSnapshot, CodexUsage, CursorUsage, StatusLevel

STATUS_EMOJI = {
    StatusLevel.GREEN: "🟢",
    StatusLevel.YELLOW: "🟡",
    StatusLevel.RED: "🔴",
}

STALE_AFTER = timedelta(minutes=5)


class StateStore:
    def __init__(self) -> None:
        self._cursor: CursorUsage | None = None
        self._codex: CodexUsage | None = None

    def update(
        self,
        cursor: CursorUsage | None = None,
        codex: CodexUsage | None = None,
    ) -> None:
        if cursor is not None:
            if cursor.error is None or self._cursor is None:
                self._cursor = cursor
            else:
                self._cursor = CursorUsage(
                    auto_percent=self._cursor.auto_percent,
                    api_percent=self._cursor.api_percent,
                    billing_cycle_end=self._cursor.billing_cycle_end,
                    fetched_at=cursor.fetched_at,
                    error=cursor.error,
                )
        if codex is not None:
            if codex.error is None or self._codex is None:
                self._codex = codex
            else:
                self._codex = CodexUsage(
                    five_hour_used_percent=self._codex.five_hour_used_percent,
                    five_hour_reset_seconds=self._codex.five_hour_reset_seconds,
                    seven_day_used_percent=self._codex.seven_day_used_percent,
                    seven_day_reset_seconds=self._codex.seven_day_reset_seconds,
                    fetched_at=codex.fetched_at,
                    error=codex.error,
                )

    def snapshot(self) -> AppSnapshot:
        return AppSnapshot(cursor=self._cursor, codex=self._codex)

    def _cursor_display(self) -> str:
        if self._cursor is None or self._cursor.error:
            return "?"
        return f"{self._cursor.auto_percent:.0f}"

    def _codex_display(self) -> str:
        if self._codex is None or self._codex.error:
            return "?"
        return f"{self._codex.five_hour_used_percent:.0f}"

    def menubar_title(self) -> str:
        if self._cursor is None and self._codex is None:
            return "⚠ Usage unavailable"
        emoji = STATUS_EMOJI[self.status_level()]
        return f"{emoji} C {self._cursor_display()}% · X {self._codex_display()}%"

    def status_level(self) -> StatusLevel:
        percents: list[float] = []
        if self._cursor and not self._cursor.error:
            percents.append(self._cursor.auto_percent)
        if self._codex and not self._codex.error:
            percents.append(self._codex.five_hour_used_percent)
        if not percents:
            return StatusLevel.YELLOW
        return StatusLevel.from_percent(max(percents))

    def is_stale(self) -> bool:
        now = datetime.now(timezone.utc)
        for usage in (self._cursor, self._codex):
            if usage and not usage.error:
                if now - usage.fetched_at > STALE_AFTER:
                    return True
        return False
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_state.py -v
```

Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/usage_tracker/state.py tests/test_state.py
git commit -m "feat: StateStore — 메뉴바 제목 및 상태 계산"
```

---

### Task 7: AlertService

**파일:**
- Create: `src/usage_tracker/alerts.py`
- Create: `tests/test_alerts.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_alerts.py`:

```python
from usage_tracker.alerts import AlertService
from usage_tracker.models import CodexUsage, CursorUsage
from datetime import datetime, timezone


def test_alert_fires_once_per_threshold():
    fired: list[tuple[str, int]] = []

    def notify(service: str, percent: float, threshold: int) -> None:
        fired.append((service, threshold))

    alerts = AlertService(warn=80, critical=90, notify=notify)
    cursor = CursorUsage(85, 10, datetime.now(timezone.utc), datetime.now(timezone.utc))
    codex = CodexUsage(30, 0, 20, 0, datetime.now(timezone.utc))

    alerts.check(cursor, codex)
    alerts.check(cursor, codex)

    assert fired.count(("Cursor", 80)) == 1
    assert fired.count(("Cursor", 90)) == 0


def test_alert_resets_on_codex_window_change():
    fired: list[tuple[str, int]] = []

    def notify(service: str, percent: float, threshold: int) -> None:
        fired.append((service, threshold))

    alerts = AlertService(warn=80, critical=90, notify=notify)
    codex1 = CodexUsage(85, 100, 20, 0, datetime.now(timezone.utc))
    codex2 = CodexUsage(85, 200, 20, 0, datetime.now(timezone.utc))

    alerts.check(None, codex1)
    alerts.check(None, codex2)

    assert len(fired) == 2
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_alerts.py -v
```

Expected: FAIL

- [ ] **Step 3: alerts.py 구현**

`src/usage_tracker/alerts.py`:

```python
from __future__ import annotations

from typing import Callable

from usage_tracker.models import CodexUsage, CursorUsage

NotifyFn = Callable[[str, float, int], None]


class AlertService:
    def __init__(
        self,
        warn: int = 80,
        critical: int = 90,
        notify: NotifyFn | None = None,
    ) -> None:
        self._warn = warn
        self._critical = critical
        self._notify = notify or (lambda *_: None)
        self._fired: set[tuple[str, int, str]] = set()

    def _period_key(self, service: str, usage: CursorUsage | CodexUsage) -> str:
        if isinstance(usage, CursorUsage):
            return f"{service}:{usage.billing_cycle_end.isoformat()}"
        return f"{service}:{usage.five_hour_reset_seconds}"

    def _check_metric(
        self,
        service: str,
        percent: float,
        usage: CursorUsage | CodexUsage,
    ) -> None:
        period = self._period_key(service, usage)
        for threshold in (self._warn, self._critical):
            key = (service, threshold, period)
            if percent >= threshold and key not in self._fired:
                self._notify(service, percent, threshold)
                self._fired.add(key)

    def check(
        self,
        cursor: CursorUsage | None,
        codex: CodexUsage | None,
    ) -> None:
        if cursor and not cursor.error:
            self._check_metric("Cursor", cursor.auto_percent, cursor)
        if codex and not codex.error:
            self._check_metric("Codex", codex.five_hour_used_percent, codex)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_alerts.py -v
```

Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/usage_tracker/alerts.py tests/test_alerts.py
git commit -m "feat: 임계치 알림 서비스 추가"
```

---

### Task 8: Popover 텍스트 빌더

**파일:**
- Create: `src/usage_tracker/popover.py`
- Create: `tests/test_popover.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_popover.py`:

```python
from datetime import datetime, timezone

from usage_tracker.models import AppSnapshot, CodexUsage, CursorUsage
from usage_tracker.popover import build_detail_text, format_duration


def test_format_duration():
    assert format_duration(3661) == "1h 1m"


def test_build_detail_text():
    snapshot = AppSnapshot(
        cursor=CursorUsage(38, 12, datetime(2026, 5, 2, tzinfo=timezone.utc), datetime.now(timezone.utc)),
        codex=CodexUsage(52, 12000, 41, 345600, datetime.now(timezone.utc)),
    )
    text = build_detail_text(snapshot, stale=False)

    assert "Cursor (Pro+)" in text
    assert "Auto+Composer" in text
    assert "38%" in text
    assert "API" in text
    assert "12%" in text
    assert "Codex (Team)" in text
    assert "5시간" in text
    assert "1주" in text
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_popover.py -v
```

Expected: FAIL

- [ ] **Step 3: popover.py 구현**

`src/usage_tracker/popover.py`:

```python
from __future__ import annotations

from usage_tracker.models import AppSnapshot


def format_duration(seconds: int) -> str:
    hours, rem = divmod(max(seconds, 0), 3600)
    minutes = rem // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def progress_bar(percent: float, width: int = 10) -> str:
    filled = round(min(max(percent, 0), 100) / 100 * width)
    return "█" * filled + "░" * (width - filled)


def build_detail_text(snapshot: AppSnapshot, stale: bool) -> str:
    lines: list[str] = []

    lines.append("Cursor (Pro+)")
    if snapshot.cursor and not snapshot.cursor.error:
        c = snapshot.cursor
        lines.append(f"  Auto+Composer  {c.auto_percent:.0f}%  {progress_bar(c.auto_percent)}")
        lines.append(f"  API            {c.api_percent:.0f}%  {progress_bar(c.api_percent)}")
        lines.append(f"  리셋: {c.billing_cycle_end.strftime('%Y-%m-%d')}")
    elif snapshot.cursor and snapshot.cursor.error:
        lines.append(f"  ⚠ {snapshot.cursor.error}")
    else:
        lines.append("  데이터 없음")

    lines.append("")
    lines.append("Codex (Team)")
    if snapshot.codex and not snapshot.codex.error:
        x = snapshot.codex
        lines.append(
            f"  5시간  {x.five_hour_used_percent:.0f}%  "
            f"{progress_bar(x.five_hour_used_percent)}  ({format_duration(x.five_hour_reset_seconds)})"
        )
        lines.append(
            f"  1주    {x.seven_day_used_percent:.0f}%  "
            f"{progress_bar(x.seven_day_used_percent)}  ({format_duration(x.seven_day_reset_seconds)})"
        )
    elif snapshot.codex and snapshot.codex.error:
        lines.append(f"  ⚠ {snapshot.codex.error}")
    else:
        lines.append("  데이터 없음")

    if stale:
        lines.append("")
        lines.append("⚠ 5분 이상 갱신되지 않음")

    return "\n".join(lines)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
pytest tests/test_popover.py -v
```

Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/usage_tracker/popover.py tests/test_popover.py
git commit -m "feat: 상세 breakdown 텍스트 빌더 추가"
```

---

### Task 9: rumps 메뉴바 앱 + 폴링

**파일:**
- Create: `src/usage_tracker/main.py`

- [ ] **Step 1: main.py 구현**

`src/usage_tracker/main.py`:

```python
from __future__ import annotations

import concurrent.futures

import rumps

from usage_tracker.alerts import AlertService
from usage_tracker.codex_fetcher import CodexFetcher
from usage_tracker.config import load_config
from usage_tracker.cursor_fetcher import CursorFetcher
from usage_tracker.popover import build_detail_text
from usage_tracker.state import StateStore


class UsageTrackerApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("Usage Tracker", quit_button=None)
        self.config = load_config()
        self.state = StateStore()
        self.cursor_fetcher = CursorFetcher(self.config.cursor_session_token)
        self.codex_fetcher = CodexFetcher()
        self.alerts = AlertService(
            warn=self.config.alert_threshold_warn,
            critical=self.config.alert_threshold_critical,
            notify=self._send_notification,
        )

        self.detail_item = rumps.MenuItem("상세 정보 로딩 중...", callback=None)
        self.menu = [
            self.detail_item,
            None,
            rumps.MenuItem("지금 새로고침", callback=self.refresh_now),
            rumps.MenuItem("설정 안내", callback=self.show_settings_help),
            None,
            rumps.MenuItem("종료", callback=self.quit_app),
        ]

        self.timer = rumps.Timer(self.poll, self.config.poll_interval_seconds)
        self.timer.start()
        self.poll(None)

    def _send_notification(self, service: str, percent: float, threshold: int) -> None:
        rumps.notification(
            title=f"{service} 사용량 {threshold}% 도달",
            subtitle=f"현재 {percent:.0f}% 사용 중",
            message="한도를 확인하세요.",
        )

    def poll(self, _sender) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            cursor_future = pool.submit(self.cursor_fetcher.fetch)
            codex_future = pool.submit(self.codex_fetcher.fetch)
            cursor = cursor_future.result()
            codex = codex_future.result()

        self.state.update(cursor=cursor, codex=codex)
        self.alerts.check(cursor, codex)
        self.title = self.state.menubar_title()
        self.detail_item.title = build_detail_text(
            self.state.snapshot(),
            stale=self.state.is_stale(),
        )

    @rumps.clicked("지금 새로고침")
    def refresh_now(self, _sender) -> None:
        self.poll(None)

    @rumps.clicked("설정 안내")
    def show_settings_help(self, _sender) -> None:
        rumps.alert(
            title="Cursor 토큰 설정",
            message=(
                "1. cursor.com/dashboard/usage 접속\n"
                "2. DevTools → Cookies → WorkosCursorSessionToken 복사\n"
                "3. 프로젝트 루트 .env 파일에 CURSOR_SESSION_TOKEN=... 저장\n\n"
                "Codex는 codex login으로 이미 인증되어 있으면 추가 설정 불필요"
            ),
        )

    @rumps.clicked("종료")
    def quit_app(self, _sender) -> None:
        rumps.quit_application()


def main() -> None:
    UsageTrackerApp().run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 전체 테스트 실행**

```bash
pytest -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 3: 수동 실행 테스트**

```bash
cp .env.example .env
# .env에 CURSOR_SESSION_TOKEN 입력 후
usage-tracker
```

Expected:
- 메뉴바에 `🟢 C 38% · X 52%` 형식 표시
- 클릭 시 상세 breakdown 메뉴 항목 표시
- 60초마다 자동 갱신

- [ ] **Step 4: 커밋**

```bash
git add src/usage_tracker/main.py
git commit -m "feat: rumps 메뉴바 앱 및 폴링 루프 추가"
```

---

### Task 10: README

**파일:**
- Create: `README.md`

- [ ] **Step 1: README 작성**

`README.md`에 포함할 내용:
- 프로젝트 설명 (한 줄)
- 요구사항: macOS, Python 3.11+, codex CLI
- 설치: `pip install -e ".[dev]"`
- Cursor 토큰 설정 3단계
- 실행: `usage-tracker`
- 테스트: `pytest -v`
- 알려진 제한: Cursor 비공식 API, 토큰 만료 시 재설정 필요

- [ ] **Step 2: 커밋**

```bash
git add README.md
git commit -m "docs: README 추가"
```

---

## 스펙 커버리지 자체 검토

| 스펙 요구사항 | 해당 Task |
|--------------|-----------|
| 메뉴바 `C {auto}% · X {5h}%` | Task 6, 9 |
| Popover 상세 breakdown | Task 8, 9 |
| 색상 (green/yellow/red) | Task 2, 6, 9 |
| 80%/90% 알림 + 중복 방지 | Task 7, 9 |
| Cursor usage-summary | Task 4 |
| Codex rateLimits | Task 5 |
| 60초 폴링 + 병렬 fetch | Task 9 |
| 부분 실패 시 graceful degrade | Task 4, 5, 6 |
| .env 설정 | Task 1, 3 |
| 단위 테스트 (fixture 기반) | Task 2–8 |

**누락 없음.**

---

## 실행 방법 선택

계획서 저장 위치: `docs/superpowers/plans/2026-06-12-usage-tracker.md`

**두 가지 실행 옵션:**

1. **Subagent-Driven (권장)** — 태스크마다 새 서브에이전트 실행, 태스크 간 리뷰, 빠른 반복
2. **Inline Execution** — 이 세션에서 `executing-plans` 스킬로 배치 실행, 체크포인트마다 리뷰

어떤 방식으로 진행할까요?
