#!/bin/bash
set -euo pipefail

PLIST_LABEL="com.usage-tracker.menubar"
PLIST_NAME="${PLIST_LABEL}.plist"
LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
PLIST_PATH="${LAUNCH_AGENTS}/${PLIST_NAME}"
WRAPPER="${HOME}/Library/Application Support/usage-tracker/run.sh"

launchctl bootout "gui/$(id -u)/${PLIST_LABEL}" 2>/dev/null || true

if [[ -f "${PLIST_PATH}" ]]; then
  rm "${PLIST_PATH}"
fi

if [[ -f "${WRAPPER}" ]]; then
  rm "${WRAPPER}"
fi

echo "✓ 자동 시작 해제 완료"
