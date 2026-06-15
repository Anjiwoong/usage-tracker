from usage_tracker.icons import BUNDLED_CLAUDE_ICON, claude_icon_path


def test_bundled_claude_icon_exists():
    assert BUNDLED_CLAUDE_ICON.is_file()


def test_claude_icon_path_uses_bundled_fallback():
    assert claude_icon_path() is not None
    assert claude_icon_path().endswith("claude.png")
