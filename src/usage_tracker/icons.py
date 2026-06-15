from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
BUNDLED_CLAUDE_ICON = _PACKAGE_DIR / "assets" / "claude.png"

CURSOR_ICON_CANDIDATES = (
    "/Applications/Cursor.app/Contents/Resources/Cursor.icns",
    "/Applications/Cursor.app/Contents/Resources/AppIcon.icns",
)

CODEX_ICON_CANDIDATES = (
    "/Applications/Codex.app/Contents/Resources/icon.icns",
    "/Applications/Codex.app/Contents/Resources/app.icns",
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


@lru_cache(maxsize=2)
def cursor_icon_path() -> str | None:
    return resolve_icon_path(CURSOR_ICON_CANDIDATES)


@lru_cache(maxsize=2)
def codex_icon_path() -> str | None:
    return resolve_icon_path(CODEX_ICON_CANDIDATES)


@lru_cache(maxsize=2)
def claude_icon_path() -> str | None:
    return resolve_icon_path(CLAUDE_ICON_CANDIDATES)
