from __future__ import annotations

import os
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
BUNDLED_CLAUDE_ICON = _PACKAGE_DIR / "assets" / "claude.png"
BUNDLED_CODEX_ICON = _PACKAGE_DIR / "assets" / "codex.png"

CURSOR_ICON_CANDIDATES = (
    "/Applications/Cursor.app/Contents/Resources/Cursor.icns",
    "/Applications/Cursor.app/Contents/Resources/AppIcon.icns",
)

CODEX_ICON_CANDIDATES = (
    "/Applications/Codex.app/Contents/Resources/icon.icns",
    "/Applications/Codex.app/Contents/Resources/app.icns",
    "/Applications/ChatGPT.app/Contents/Resources/icon-codex-dark-color.png",
    "/Applications/ChatGPT.app/Contents/Resources/icon-codex-light.png",
    str(BUNDLED_CODEX_ICON),
)

CLAUDE_ICON_CANDIDATES = (
    "/Applications/Claude.app/Contents/Resources/AppIcon.icns",
    "/Applications/Claude.app/Contents/Resources/app.icns",
    str(BUNDLED_CLAUDE_ICON),
)


def resolve_icon_path(candidates: tuple[str, ...]) -> str | None:
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def cursor_icon_path() -> str | None:
    return resolve_icon_path(CURSOR_ICON_CANDIDATES)


def codex_icon_path() -> str | None:
    return resolve_icon_path(CODEX_ICON_CANDIDATES)


def claude_icon_path() -> str | None:
    return resolve_icon_path(CLAUDE_ICON_CANDIDATES)
