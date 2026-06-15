#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_LABEL="com.usage-tracker.menubar"
PLIST_NAME="${PLIST_LABEL}.plist"
LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
LOG_DIR="${HOME}/Library/Logs/usage-tracker"
WRAPPER="${HOME}/Library/Application Support/usage-tracker/run.sh"
PYTHON="${PROJECT_DIR}/.venv/bin/python3.12"

if [[ ! -x "${PYTHON}" ]]; then
  echo "오류: ${PYTHON} 을 찾을 수 없습니다."
  echo "먼저 가상환경을 만들고 설치하세요: pip install -e \".[dev]\""
  exit 1
fi

mkdir -p "${LOG_DIR}" "${LAUNCH_AGENTS}" "$(dirname "${WRAPPER}")"

cat > "${WRAPPER}" <<EOF
#!/bin/bash
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
cd "${PROJECT_DIR}"
exec "${PYTHON}" -m usage_tracker.main
EOF
chmod +x "${WRAPPER}"

cat > "${LAUNCH_AGENTS}/${PLIST_NAME}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${WRAPPER}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <dict>
    <key>SuccessfulExit</key>
    <false/>
  </dict>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/stdout.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/stderr.log</string>
  <key>LimitLoadToSessionType</key>
  <string>Aqua</string>
  <key>ProcessType</key>
  <string>Interactive</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/${PLIST_LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "${LAUNCH_AGENTS}/${PLIST_NAME}"

sleep 2
if pgrep -f "usage_tracker.main" >/dev/null 2>&1; then
  echo "✓ 자동 시작 등록 및 실행 완료"
else
  echo "⚠ plist는 등록됐지만 앱이 시작되지 않았습니다."
  echo "  로그 확인: tail ~/Library/Logs/usage-tracker/stderr.log"
  echo ""
  echo "  Desktop 폴더 권한 문제일 수 있습니다."
  echo "  시스템 설정 → 개인정보 보호 → 파일 및 폴더 → /bin/bash 에"
  echo "  '데스크탑 폴더' 접근을 허용하거나, 프로젝트를 ~/Projects 로 옮겨주세요."
fi

echo ""
echo "  plist: ${LAUNCH_AGENTS}/${PLIST_NAME}"
echo "  wrapper: ${WRAPPER}"
echo "  해제: scripts/uninstall-autostart.sh"
