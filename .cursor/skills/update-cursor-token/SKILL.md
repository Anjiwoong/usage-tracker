---
name: update-cursor-token
description: >-
  Updates usage-tracker's .env CURSOR_SESSION_TOKEN from the Chrome
  WorkosCursorSessionToken cookie (or a pasted token), then restarts the
  menubar app so the new token is loaded. Use when the user says the Cursor
  token changed, asks to refresh/update/sync the Cursor session token, asks
  to restart usage-tracker after a token change, mentions
  WorkosCursorSessionToken, or invokes update-cursor-token. Korean triggers
  include 커서 토큰, 토큰 업데이트, 토큰 갱신, 세션 토큰, 프로그램 재시작.
---

# Update Cursor Token

usage-tracker는 Cursor 사용량을 `WorkosCursorSessionToken` 쿠키로 조회하고, 토큰은 프로세스 시작 때 한 번만 읽는다. 이 스킬은 `.env`를 갱신한 뒤 앱을 **직접 재시작**한다. 사용자에게 재시작하라고 안내만 하지 말 것.

## 할 일

1. 아래 스크립트를 **실행**한다. 토큰 값을 채팅에 그대로 출력하지 않는다.
2. 스크립트가 토큰 동기화와 앱 재시작을 모두 한다.
3. 결과를 짧게 보고한다. 토큰 전체는 말하지 말고 `length`, `suffix`, `changed`, `restarted`만 말한다.

## 토큰 소스

**사용자가 이번 메시지에 토큰을 붙여넣었으면** stdin으로 넘긴다. 명령줄 인자로 넣지 않는다(프로세스 목록에 남음).

```bash
python3 .cursor/skills/update-cursor-token/scripts/update_cursor_token.py --from-stdin <<'EOF'
PASTED_TOKEN
EOF
```

**붙여넣은 값이 없으면** Chrome(없으면 Edge/Brave/Arc) 쿠키에서 `WorkosCursorSessionToken`을 읽어 `.env`에 쓴 뒤 앱을 재시작한다.

```bash
python3 .cursor/skills/update-cursor-token/scripts/update_cursor_token.py
```

첫 실행 때 macOS Keychain 허용 대화상자가 뜰 수 있다. 사용자가 거부하면 스크립트가 실패하므로, cursor.com에 로그인된 뒤 다시 실행하라고 안내한다.

## 재시작

스크립트가 처리한다. 별도 `kill` / `launchctl` / `usage-tracker` 명령을 에이전트가 직접 치지 말 것.

1. LaunchAgent `com.usage-tracker.menubar`가 있으면 `launchctl kickstart -k`로 재시작
2. 없으면 기존 `usage_tracker.main`을 종료하고 `.venv`로 다시 실행

토큰이 이전과 같아도 재시작한다. `.env`를 프로세스에 다시 읽히기 위해서다.

## 결과 처리

스크립트 stdout은 JSON이다. `ok`, `changed`, `source`, `length`, `suffix`, `restarted`, `method`, `pid`만 사용한다.

- `ok: true`, `restarted: true` → 토큰 반영 후 앱 재시작 완료
- `ok: true`, `changed: false`, `restarted: true` → 토큰은 동일, 앱만 재시작
- `restarted: false` → `error`를 전달. 토큰을 추측해서 채우지 말 것
- `ok: false` → 토큰 추출 실패. 재시작하지 않음

`.env`를 직접 열어서 토큰을 읽거나 채팅에 인용하지 말 것.

## 수동 폴백

브라우저 추출이 실패했고 사용자가 토큰을 아직 안 줬으면, 아래만 안내하고 기다린다. 재시작은 토큰을 받은 뒤 스크립트가 한다.

1. https://cursor.com/dashboard/usage 로그인
2. DevTools → Application → Cookies → `WorkosCursorSessionToken` 복사
3. 채팅에 붙여넣기 (또는 스크립트 `--from-stdin`)
