# Usage Tracker — Design Spec

**Date:** 2026-06-12  
**Status:** Draft — awaiting user review  
**Scope:** Personal macOS menubar app for Cursor Pro+ and Codex (ChatGPT Team) usage

---

## 1. Goal

A lightweight macOS menubar widget that shows Cursor and Codex usage at a glance while coding. Default view is compact; clicking opens a popover with full breakdowns.

### Success Criteria

- Menubar shows `C {auto}% · X {5h}%` within 60 seconds of usage change
- Popover shows Cursor (Auto+Composer, API) and Codex (5-hour, weekly) on click
- Icon color reflects worst default metric: green (<50%), yellow (50–80%), red (≥80%)
- macOS notifications at 80% and 90% thresholds (once per threshold per billing/window period)
- Runs locally only; no cloud deployment

### Out of Scope (v1)

- Multi-account support
- Usage history / charts
- Web dashboard
- Windows/Linux support
- Official Cursor Enterprise API (user is Pro+)

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MenubarApp (rumps)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ StateStore  │  │ AlertService │  │ PopoverBuilder │ │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘ │
│         │                │                   │          │
│  ┌──────┴────────────────┴───────────────────┴────────┐ │
│  │              PollScheduler (60s interval)          │ │
│  └──────┬──────────────────────────────┬──────────────┘ │
└─────────┼──────────────────────────────┼────────────────┘
          │                              │
   ┌──────▼──────┐                ┌──────▼──────┐
   │CursorFetcher│                │ CodexFetcher│
   │  (HTTP)     │                │ (JSON-RPC)  │
   └──────┬──────┘                └──────┬──────┘
          │                              │
   cursor.com/api/usage-summary    Codex app-server (local)
   + WorkosCursorSessionToken      account/rateLimits/read
```

### Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Menubar UI | Python 3.11+ + `rumps` | Fast MVP, good menubar support on macOS |
| HTTP | `httpx` | Async-friendly, simple API for Cursor |
| Codex RPC | subprocess + stdin/stdout JSON-RPC | Matches codex-quota pattern; no extra deps |
| Config | `.env` + optional macOS Keychain | Simple setup; Keychain optional v1.1 |
| Notifications | `rumps.notification` | Native macOS alerts |
| Packaging | `pyproject.toml` + `uv` or `pip` | Standard Python project layout |

---

## 3. Components

### 3.1 CursorFetcher

**Purpose:** Fetch Cursor Pro+ usage from unofficial dashboard API.

**Endpoint:** `GET https://cursor.com/api/usage-summary`

**Auth:** Cookie header `WorkosCursorSessionToken={token}` from config.

**Parsed fields:**

```python
@dataclass
class CursorUsage:
    auto_percent: float      # individualUsage.plan.autoPercentUsed
    api_percent: float       # individualUsage.plan.apiPercentUsed
    billing_cycle_end: datetime
    fetched_at: datetime
    error: str | None
```

**Notes:**
- Pro+ returns spend-based percentages in `autoPercentUsed` / `apiPercentUsed`
- Unofficial API — may break; log response shape changes
- On 401/403: set error state, prompt user to refresh token (menu item)

### 3.2 CodexFetcher

**Purpose:** Read Codex rate limits via local app-server JSON-RPC.

**Flow:**
1. Spawn `codex app-server` (or connect to existing instance if detectable)
2. Send `initialize` → `initialized`
3. Send `account/rateLimits/read`
4. Parse `five_hour` and `seven_day` buckets

**Parsed fields:**

```python
@dataclass
class CodexUsage:
    five_hour_used_percent: float
    five_hour_reset_seconds: int
    seven_day_used_percent: float
    seven_day_reset_seconds: int
    fetched_at: datetime
    error: str | None
```

**Notes:**
- Reuses ChatGPT Team auth already configured in Codex CLI
- If Codex not installed or auth expired: error state with actionable message

### 3.3 StateStore

**Purpose:** Single source of truth for latest fetch results and alert deduplication.

- Holds `CursorUsage | None`, `CodexUsage | None`
- Tracks which threshold alerts already fired this period (avoid spam)
- Computes menubar title: `C {auto:.0f}% · X {5h:.0f}%`
- Computes status color from `max(auto_percent, five_hour_used_percent)` for default metrics

### 3.4 AlertService

**Purpose:** Fire macOS notifications when thresholds crossed.

| Threshold | Cursor metric | Codex metric | Behavior |
|-----------|---------------|--------------|----------|
| 80% | auto_percent | five_hour_used_percent | Notify once per period |
| 90% | auto_percent | five_hour_used_percent | Notify once per period |

- Reset alert flags when Codex 5h window resets or Cursor billing cycle rolls
- Title color also updates via rumps icon/template (green/yellow/red dot prefix or emoji)

### 3.5 MenubarApp (rumps)

**Default menubar:** `🟢 C 38% · X 52%` (emoji/color reflects status)

**Menu items:**
- Click title → show popover (rumps window or custom NSWindow)
- "Refresh Now" — force immediate poll
- "Settings…" — open `.env` location / token setup instructions
- "Quit"

**Popover content (text-based v1):**

```
Cursor (Pro+)
  Auto+Composer   38%  ████░░░░░░
  API             12%  ██░░░░░░░░
  Resets: May 2

Codex (Team)
  5-hour          52%  █████░░░░░  (3h 20m)
  Weekly          41%  ████░░░░░░  (4d 8h)

Updated 12s ago
```

### 3.6 PollScheduler

- Background thread or `rumps.Timer` every **60 seconds**
- Fetch Cursor and Codex **in parallel** (`concurrent.futures`)
- On failure: keep last good data, show stale indicator in popover ("Updated 5m ago ⚠")

---

## 4. Data Flow

```
App launch
  → Load config (.env: CURSOR_SESSION_TOKEN)
  → Initial fetch (Cursor + Codex parallel)
  → Update menubar title + color
  → Start 60s timer

Every 60s (or manual refresh)
  → CursorFetcher.fetch() ──┐
  → CodexFetcher.fetch()  ──┼→ StateStore.update()
                              → AlertService.check_thresholds()
                              → MenubarApp.refresh_display()

User clicks menubar
  → PopoverBuilder.render(StateStore.snapshot())
```

---

## 5. Configuration

**`.env` (gitignored):**

```env
CURSOR_SESSION_TOKEN=your_workos_cursor_session_token
POLL_INTERVAL_SECONDS=60
ALERT_THRESHOLD_WARN=80
ALERT_THRESHOLD_CRITICAL=90
```

**Token setup (one-time):**
1. Open `https://cursor.com/dashboard/usage` while logged in
2. DevTools → Application → Cookies → `WorkosCursorSessionToken`
3. Paste into `.env`

**Codex:** No extra config if `codex` CLI is already authenticated.

---

## 6. Error Handling

| Failure | User-visible behavior |
|---------|----------------------|
| Cursor 401/403 | Menubar: `C ? · X 52%`; popover shows "Cursor: session expired — update token" |
| Cursor network error | Keep last known Cursor data; stale warning after 5 min |
| Codex auth required | Menubar: `C 38% · X ?`; popover shows "Codex: run `codex login`" |
| Codex app-server fail | Retry next poll; log error |
| Both fail | `⚠ Usage unavailable` in menubar |

No crash on partial failure — always show what's available.

---

## 7. Project Structure

```
usage-tracker/
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
├── src/
│   └── usage_tracker/
│       ├── __init__.py
│       ├── main.py              # rumps app entry
│       ├── config.py
│       ├── models.py            # CursorUsage, CodexUsage dataclasses
│       ├── cursor_fetcher.py
│       ├── codex_fetcher.py
│       ├── state.py
│       ├── alerts.py
│       └── popover.py
└── docs/superpowers/specs/
    └── 2026-06-12-usage-tracker-design.md
```

---

## 8. Testing Strategy

| Test | Method |
|------|--------|
| Cursor response parsing | Unit tests with fixture JSON from usage-summary |
| Codex response parsing | Unit tests with fixture rateLimits JSON |
| Alert deduplication | Unit test: same threshold doesn't fire twice |
| Menubar title format | Unit test: StateStore.title property |
| Integration | Manual: run app, verify menubar updates, click popover |

No E2E against live APIs in CI (tokens required). Fixtures only.

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Cursor unofficial API breaks | Log raw response; README documents how to update parser |
| Session token expires (~weeks) | Clear error message + Settings menu with setup steps |
| Codex app-server protocol changes | Isolate in CodexFetcher; reference codex-quota |
| rumps popover limitations | v1 text menu items if popover is awkward; upgrade to PyObjC window in v1.1 |

---

## 10. Future (post-v1)

- macOS Keychain for token storage
- LaunchAgent for auto-start on login
- SQLite history + daily usage chart
- Swift rewrite if Python feels too heavy
