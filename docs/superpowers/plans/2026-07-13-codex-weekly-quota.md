# Codex 주간 할당량 전환 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Codex의 단일 주간 할당량을 데이터 조회, 메뉴바 상태, 알림, 상세 메뉴에 일관되게 표시한다.

**Architecture:** `CodexUsage`를 주간 버킷 하나만 표현하도록 변경하고, Codex API의 `primary` 버킷을 이 필드에 매핑한다. `StateStore`와 `AlertService`는 같은 주간 사용률 및 리셋 값을 사용하며, 팝오버는 Codex에만 `1주` 진행 바와 날짜 기준 리셋 안내를 표시한다. Claude의 이중 버킷 모델과 표시는 유지한다.

**Tech Stack:** Python 3.11, dataclasses, pytest, rumps

## Global Constraints

- Codex `rateLimits.primary`는 주간 할당량으로 해석한다.
- Codex의 `secondary`는 읽거나 저장하지 않는다.
- Cursor와 Claude의 데이터 모델 및 표시는 변경하지 않는다.
- Codex의 기존 5시간 API 호환 레이어는 만들지 않는다.
- 기존 사용자 변경 파일(`src/usage_tracker/config.py`, `src/usage_tracker/icons.py`, `src/usage_tracker/menu_style.py`)은 수정하지 않는다.

---

## 파일 구조

- `src/usage_tracker/models.py`: Codex 전용 주간 사용량 모델
- `src/usage_tracker/codex_fetcher.py`: `primary` 버킷 파싱과 오류 객체 생성
- `src/usage_tracker/state.py`: Codex 메뉴바 값·상태·마지막 정상 값 보존
- `src/usage_tracker/alerts.py`: Codex 주간 알림 주기·임계치
- `src/usage_tracker/popover.py`: Codex 요약·상세 메뉴
- `tests/test_codex_fetcher.py`, `tests/test_state.py`, `tests/test_alerts.py`, `tests/test_popover.py`: 변경된 계약의 회귀 테스트

### Task 1: Codex 주간 사용량 데이터와 상태·알림 전환

**Files:**
- Modify: `src/usage_tracker/models.py:33-41`
- Modify: `src/usage_tracker/codex_fetcher.py:31-49,107-133`
- Modify: `src/usage_tracker/state.py:50-58,82-86,110-118,153-169`
- Modify: `src/usage_tracker/alerts.py:19-23,53-58`
- Modify: `tests/test_codex_fetcher.py:15-24,76-80`
- Modify: `tests/test_state.py:17-25,43-44,61-63`
- Modify: `tests/test_alerts.py:38-42,56-61`

**Interfaces:**
- Consumes: `rateLimits.primary.usedPercent`, `rateLimits.primary.resetsAt`.
- Produces: `CodexUsage(weekly_used_percent: float, weekly_reset_seconds: int, fetched_at: datetime, plan_type: str | None = None, error: str | None = None)`.
- Produces: `StateStore`와 `AlertService`가 Codex 주간 사용률을 단일 기준값으로 사용한다.

- [ ] **Step 1: 실패하는 Codex 파서·상태·알림 테스트 작성**

`tests/test_codex_fetcher.py`의 사용량 단언을 아래와 같이 바꾼다.

```python
assert usage.weekly_used_percent == 52.0
assert usage.weekly_reset_seconds > 0
assert usage.plan_type == "team"
```

`tests/test_state.py`의 헬퍼와 호출부를 아래처럼 바꾼다.

```python
def make_codex(weekly: float = 52.0) -> CodexUsage:
    now = datetime.now(timezone.utc)
    return CodexUsage(
        weekly_used_percent=weekly,
        weekly_reset_seconds=345600,
        fetched_at=now,
    )

store.update(cursor=make_cursor(), codex=make_codex(weekly=85), claude=make_claude())
assert store.status_level() == StatusLevel.RED
```

`tests/test_alerts.py`의 Codex fixture도 새 생성자로 바꾼다.

```python
alerts.check(None, CodexUsage(weekly_used_percent=50, weekly_reset_seconds=100, fetched_at=base))
alerts.check(None, CodexUsage(weekly_used_percent=85, weekly_reset_seconds=100, fetched_at=base))
alerts.check(None, CodexUsage(weekly_used_percent=50, weekly_reset_seconds=200, fetched_at=base))
alerts.check(None, CodexUsage(weekly_used_percent=85, weekly_reset_seconds=200, fetched_at=base))
assert fired == [("Codex", 80), ("Codex", 80)]
```

- [ ] **Step 2: 테스트가 올바르게 실패하는지 확인**

Run: `pytest tests/test_codex_fetcher.py tests/test_state.py tests/test_alerts.py -v`

Expected: FAIL — `CodexUsage`에 `weekly_used_percent`와 `weekly_reset_seconds`가 없거나 기존 생성자 인수가 맞지 않는다는 오류가 발생한다.

- [ ] **Step 3: 최소 데이터·상태·알림 구현 작성**

`src/usage_tracker/models.py`의 `CodexUsage`을 다음 필드만 갖도록 바꾼다.

```python
@dataclass
class CodexUsage:
    weekly_used_percent: float
    weekly_reset_seconds: int
    fetched_at: datetime
    plan_type: str | None = None
    error: str | None = None
```

`src/usage_tracker/codex_fetcher.py`에서 `secondary`를 제거하고 `primary`만 매핑한다.

```python
return CodexUsage(
    weekly_used_percent=float(primary["usedPercent"]),
    weekly_reset_seconds=reset_seconds(primary),
    fetched_at=datetime.now(timezone.utc),
    plan_type=rate_limits.get("planType"),
)
```

세 오류 반환 경로도 아래처럼 두 주간 필드를 0으로 지정한다.

```python
CodexUsage(
    weekly_used_percent=0,
    weekly_reset_seconds=0,
    fetched_at=now,
    error=error_message,
)
```

`src/usage_tracker/state.py`의 Codex 접근을 모두 `weekly_used_percent`와 `weekly_reset_seconds`로 바꾼다. 오류 상태에서 마지막 정상 데이터를 유지하는 생성 코드는 다음과 같아야 한다.

```python
self._codex = CodexUsage(
    weekly_used_percent=self._codex.weekly_used_percent,
    weekly_reset_seconds=self._codex.weekly_reset_seconds,
    fetched_at=codex.fetched_at,
    plan_type=self._codex.plan_type,
    error=codex.error,
)
```

`src/usage_tracker/alerts.py`는 Codex의 주간 리셋을 기간 키로 사용하고 주간 사용률로 임계치를 확인한다.

```python
return f"{service}:{usage.weekly_reset_seconds}"

if codex and not codex.error:
    self._check_metric("Codex", codex.weekly_used_percent, codex)
```

- [ ] **Step 4: 대상 테스트 통과 확인**

Run: `pytest tests/test_codex_fetcher.py tests/test_state.py tests/test_alerts.py -v`

Expected: PASS — Codex의 사용률, 메뉴바 상태, 알림 주기가 모두 주간 필드를 사용한다.

- [ ] **Step 5: 변경 사항 커밋**

Run: `git add src/usage_tracker/models.py src/usage_tracker/codex_fetcher.py src/usage_tracker/state.py src/usage_tracker/alerts.py tests/test_codex_fetcher.py tests/test_state.py tests/test_alerts.py`

Run: `git commit -m "feat: Codex 주간 할당량 사용"`

### Task 2: Codex 1주 전용 메뉴 표시

**Files:**
- Modify: `src/usage_tracker/popover.py:134-141,213-224`
- Modify: `tests/test_popover.py:73-79,90-105,108-126,138-220`

**Interfaces:**
- Consumes: `CodexUsage.weekly_used_percent`, `CodexUsage.weekly_reset_seconds`, `CodexUsage.fetched_at`.
- Produces: `codex_summary_label(snapshot)`이 `format_metric_line("1주", weekly_used_percent)`를 반환한다.
- Produces: `_codex_detail_section(snapshot)`이 `1주` 사용량 줄과 주간 리셋 안내 줄만 반환한다.

- [ ] **Step 1: 실패하는 Codex 팝오버 테스트 작성**

`tests/test_popover.py`의 모든 `CodexUsage(...)` 생성은 다음 형태로 바꾼다.

```python
CodexUsage(52, 345600, datetime.now(timezone.utc), plan_type="team")
```

요약 라벨 검증을 아래처럼 바꾼다.

```python
assert codex_summary_label(snapshot) == format_metric_line("1주", 52)
```

Codex와 Claude를 구분하는 상세 메뉴 테스트를 추가한다.

```python
codex_lines = build_detail_lines(
    AppSnapshot(codex=CodexUsage(52, 345600, datetime.now(timezone.utc))),
    stale=False,
)
assert any("1주" in line for line in codex_lines)
assert not any("5시간" in line for line in codex_lines)
assert any("4일" in line and "까지" in line for line in codex_lines)
```

기존 Claude 포함 상세 메뉴 테스트는 `5시간`이 존재한다는 단언을 유지해 Claude 회귀를 막는다.

- [ ] **Step 2: 테스트가 올바르게 실패하는지 확인**

Run: `pytest tests/test_popover.py -v`

Expected: FAIL — Codex 요약이 아직 `5시간` 라벨과 이전 속성을 참조한다.

- [ ] **Step 3: 최소 팝오버 구현 작성**

`codex_summary_label`을 다음처럼 바꾼다.

```python
def codex_summary_label(snapshot: AppSnapshot) -> str:
    if snapshot.codex and not snapshot.codex.error:
        return format_metric_line("1주", snapshot.codex.weekly_used_percent)
    if snapshot.codex and snapshot.codex.error:
        return "⚠  조회 실패"
    return "—"
```

`_codex_detail_section`에서 5시간 줄과 시각 기준 리셋 줄을 제거하고 다음 두 줄만 남긴다.

```python
lines.append(format_metric_line("1주", usage.weekly_used_percent))
lines.append(format_codex_weekly_reset_line(usage.fetched_at, usage.weekly_reset_seconds))
```

`format_codex_five_hour_reset_line`은 Claude가 사용하므로 삭제하지 않는다.

- [ ] **Step 4: 팝오버 테스트 통과 확인**

Run: `pytest tests/test_popover.py -v`

Expected: PASS — Codex는 1주만 표시하고 Claude의 5시간·1주 표시는 유지된다.

- [ ] **Step 5: 전체 테스트와 정적 점검 실행**

Run: `pytest -v`

Expected: PASS — 전체 테스트가 통과한다.

Run: `git diff --check`

Expected: PASS — 공백 오류가 없다.

- [ ] **Step 6: 변경 사항 커밋**

Run: `git add src/usage_tracker/popover.py tests/test_popover.py`

Run: `git commit -m "feat: Codex 메뉴에 주간 할당량만 표시"`

## 계획 자체 검토

- 명세 범위 검토: `primary`의 주간 매핑(Task 1), 단일 모델(Task 1), 요약·상세 표시(Task 2), 오류 경로(Task 1), 테스트(Task 1·2)를 모두 포함한다.
- 누락 영향 검토: 메뉴바 상태와 알림도 이전 5시간 필드를 사용하므로 Task 1에 포함했다.
- 제외 범위 검토: Claude 필드는 변경하지 않으며, Codex `secondary` 호환 처리를 추가하지 않는다.
- 일관성 검토: 모든 새 Codex 속성은 `weekly_used_percent`와 `weekly_reset_seconds`로 통일했다.
