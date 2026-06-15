# Usage Tracker

Cursor · Codex · Claude 사용량을 macOS 메뉴바에서 확인하는 개인용 앱입니다.

---

## 빠른 시작

```bash
cd usage-tracker
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
usage-tracker
```

실행되면 **메뉴바 오른쪽**에 아이콘이 나타납니다. 터미널에는 로그가 거의 출력되지 않습니다.

---

## 서비스별 설정

각 서비스는 **독립적**입니다. Cursor만 쓰거나, Codex만 쓰거나, 조합해도 됩니다. 설정·로그인이 안 된 서비스는 다른 서비스에 영향을 주지 않습니다.

### Cursor

| | |
| --- | --- |
| **필요한 것** | Cursor Pro+ (또는 사용량 대시보드 접근 가능한 계정) |
| **`.env` 필요?** | ✅ 예 |
| **인증 방식** | 브라우저 쿠키에서 세션 토큰 복사 |

**설정 방법**

1. [cursor.com/dashboard/usage](https://cursor.com/dashboard/usage) 접속
2. DevTools → Application → Cookies → `WorkosCursorSessionToken` 복사
3. 프로젝트 루트에 `.env` 생성 후 토큰 입력

```bash
cp .env.example .env
# .env 파일을 열어 아래 값 입력
# CURSOR_SESSION_TOKEN=복사한_토큰
```

토큰은 주기적으로 만료됩니다. Cursor 쪽이 조회 실패로 바뀌면 위 과정을 다시 하세요.

---

### Codex

| | |
| --- | --- |
| **필요한 것** | [Codex CLI](https://developers.openai.com/codex) + ChatGPT Team(또는 Codex 사용 가능한 플랜) |
| **`.env` 필요?** | ❌ 아니오 |
| **인증 방식** | CLI 로그인 |

**설정 방법**

```bash
# Codex CLI가 없다면 먼저 설치 (OpenAI 문서 참고)
codex login
```

`codex login`으로 이미 인증되어 있으면 **추가 설정 없음**. 앱이 로컬 `codex app-server`로 사용량을 조회합니다.

---

### Claude

| | |
| --- | --- |
| **필요한 것** | [Claude Code CLI](https://code.claude.com/docs/en/setup) + Claude Pro/Max 구독 |
| **`.env` 필요?** | ❌ 아니오 |
| **인증 방식** | CLI 로그인 |

**설정 방법**

```bash
npm install -g @anthropic-ai/claude-code   # Node.js 18+ 필요
claude login
```

`claude login` 완료 시 `~/.claude/.credentials.json`이 생성되고, 앱이 자동으로 OAuth 토큰을 읽습니다. Claude Desktop 앱은 필수가 아닙니다(아이콘은 앱에 번들되어 있음).

구독 전이거나 로그인 전이면 메뉴 요약에 `⚠ 조회 실패`가 표시됩니다. 메뉴바에는 조회 가능한 서비스만 나타납니다.

---

## 실행

### 실행

```bash
cd usage-tracker
source .venv/bin/activate
usage-tracker
```

`usage-tracker` 명령이 없으면:

```bash
python -m usage_tracker.main
```

코드를 수정했다면 실행 중인 앱을 **종료 후 다시 실행**하세요 (`pip install -e`로 설치했으면 재설치 불필요).

### 종료

메뉴바 아이콘 → **종료**, 또는 터미널에서 `Ctrl+C`

### 사용법

| 위치 | 표시 방식 |
| --- | --- |
| **메뉴바** | 조회 **성공한** 서비스만 아이콘 + 사용률(%) |
| **메뉴 상단 요약** | Cursor · Codex · Claude 항상 표시 — 실패 시 `⚠ 조회 실패` |
| **메뉴 상세** | 성공: 전체 breakdown / 실패: 제목 + 안내 문구만 |
| ↻ 지금 새로고침 | 즉시 다시 조회 |
| ⚙ 설정 안내 | 토큰·로그인 방법 요약 |
| 종료 | 앱 종료 |

60초마다 자동 갱신됩니다. 주기는 `.env`의 `POLL_INTERVAL_SECONDS`로 변경 가능 (기본 `60`).

---

## 문제 해결

| 증상 | 해결 |
| --- | --- |
| 메뉴바에 아이콘 없음 | 메뉴바 공간 확인, 터미널 오류 확인 |
| 메뉴바에 `⚠ —` | 조회 가능한 서비스가 없음 — 각 서비스 설정 확인 |
| Cursor 조회 실패 | `.env`의 `CURSOR_SESSION_TOKEN` 확인·갱신 |
| Codex 조회 실패 | `codex login` 재실행, Codex CLI 설치 확인 |
| Claude 조회 실패 | Pro/Max 구독 확인, `claude login` 재실행 |
| 자동 시작 실패 | `tail ~/Library/Logs/usage-tracker/stderr.log` |

---

## 선택 설정 (`.env`)

Cursor 토큰 외에는 모두 선택입니다.

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `CURSOR_SESSION_TOKEN` | (없음) | Cursor 세션 토큰 |
| `POLL_INTERVAL_SECONDS` | `60` | 갱신 주기(초) |
| `ALERT_THRESHOLD_WARN` | `80` | 경고 알림 임계값(%) |
| `ALERT_THRESHOLD_CRITICAL` | `90` | 위험 알림 임계값(%) |

---

## Mac 로그인 시 자동 시작

```bash
chmod +x scripts/install-autostart.sh scripts/uninstall-autostart.sh
./scripts/install-autostart.sh    # 등록
./scripts/uninstall-autostart.sh  # 해제
```

로그: `~/Library/Logs/usage-tracker/`

## 테스트

```bash
pytest -v
```

## 알려진 제한

- Cursor·Claude usage API는 비공식 엔드포인트입니다.
- Codex는 로컬 `codex app-server` JSON-RPC를 사용합니다.
- Claude 한도는 웹·앱·CLI 전체가 공유됩니다.
