# Usage Tracker

Cursor Pro+와 Codex(ChatGPT Team) 사용량을 macOS 메뉴바에서 확인하는 개인용 앱입니다.

## 요구사항

- macOS
- Python 3.11+ (권장: Homebrew `python@3.12`)
- [Codex CLI](https://developers.openai.com/codex) 설치 및 `codex login` 완료

## 설치

```bash
cd usage-tracker
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Cursor 토큰 설정

1. [cursor.com/dashboard/usage](https://cursor.com/dashboard/usage) 접속
2. DevTools → Application → Cookies → `WorkosCursorSessionToken` 복사
3. `.env` 파일 생성:

```bash
cp .env.example .env
# .env에 CURSOR_SESSION_TOKEN=... 입력
```

## 실행

### 1. 실행 전 확인

아래가 모두 준비되어 있어야 합니다.

- 가상환경 설치 완료 (`pip install -e ".[dev]"`)
- 프로젝트 루트에 `.env` 파일 생성 및 `CURSOR_SESSION_TOKEN` 입력
- Codex CLI 로그인 완료 (`codex login`)

`.env` 예시:

```bash
cp .env.example .env
# .env 파일을 열어 CURSOR_SESSION_TOKEN 값을 본인 토큰으로 교체
```

선택 환경 변수:

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `POLL_INTERVAL_SECONDS` | `60` | 사용량 갱신 주기(초) |
| `ALERT_THRESHOLD_WARN` | `80` | 경고 알림 임계값(%) |
| `ALERT_THRESHOLD_CRITICAL` | `90` | 위험 알림 임계값(%) |

### 2. 앱 실행

프로젝트 루트에서 가상환경을 활성화한 뒤 실행합니다.

```bash
cd usage-tracker
source .venv/bin/activate
usage-tracker
```

`usage-tracker` 명령이 없으면 아래 방법도 사용할 수 있습니다.

```bash
python -m usage_tracker.main
```

터미널에는 로그가 거의 출력되지 않습니다. 실행에 성공하면 **메뉴바 오른쪽**에 사용량 아이콘이 나타납니다.

### 3. 사용 방법

- 메뉴바 표시 예: `🟡 38%╱76%` (왼쪽 Cursor, 오른쪽 Codex)
- 아이콘 클릭: Cursor / Codex 상세 사용량 breakdown 확인
- `↻ 지금 새로고침`: 즉시 다시 조회
- `⚙ Cursor 토큰 설정`: 토큰 갱신 방법 안내
- `종료`: 앱 종료

Cursor 토큰이 없거나 만료되면 Cursor 쪽 수치가 비어 있거나 갱신되지 않을 수 있습니다. 이 경우 `.env`의 `CURSOR_SESSION_TOKEN`을 다시 설정하세요.

### 4. 종료

메뉴바 아이콘 → `종료`를 선택하거나, 터미널에서 실행 중이었다면 `Ctrl+C`로 종료합니다.

### 5. 실행 문제 해결

| 증상 | 확인 방법 |
| --- | --- |
| 메뉴바에 아이콘이 안 보임 | Dock/메뉴바 공간 확인, 터미널에 Python 오류가 없는지 확인 |
| Cursor 사용량이 `-` 또는 0 | `.env`의 `CURSOR_SESSION_TOKEN` 값 확인 |
| Codex 사용량이 안 나옴 | `codex login` 상태 확인, Codex CLI 설치 여부 확인 |
| 자동 시작 후 실행 안 됨 | `tail ~/Library/Logs/usage-tracker/stderr.log` 로그 확인 |

## 로그인 시 자동 시작

Mac 로그인할 때마다 자동으로 메뉴바에 뜨게 하려면:

```bash
chmod +x scripts/install-autostart.sh scripts/uninstall-autostart.sh
./scripts/install-autostart.sh
```

해제:

```bash
./scripts/uninstall-autostart.sh
```

로그: `~/Library/Logs/usage-tracker/`

## 테스트

```bash
pytest -v
```

## 알려진 제한

- Cursor API는 비공식 엔드포인트입니다. 변경될 수 있습니다.
- 세션 토큰은 주기적으로 만료됩니다. 만료 시 `.env`를 갱신하세요.
- Codex는 로컬 `codex app-server` JSON-RPC를 사용합니다.
