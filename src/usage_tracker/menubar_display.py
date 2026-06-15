from __future__ import annotations

from AppKit import (
    NSAttributedString,
    NSFont,
    NSFontAttributeName,
    NSMutableAttributedString,
    NSTextAttachment,
)

from usage_tracker.icons import codex_icon_path, cursor_icon_path
from usage_tracker.models import StatusLevel
from usage_tracker.state import STATUS_EMOJI, StateStore

ICON_SIZE = 14.0


def _scaled_icon(path: str):
    from AppKit import NSImage

    image = NSImage.alloc().initByReferencingFile_(path)
    image.setScalesWhenResized_(True)
    image.setSize_((ICON_SIZE, ICON_SIZE))
    return image


def _icon_attachment(path: str | None, fallback: str) -> NSAttributedString:
    if path:
        attachment = NSTextAttachment.alloc().init()
        attachment.setImage_(_scaled_icon(path))
        attachment.setBounds_(((0, -3, ICON_SIZE, ICON_SIZE)))
        return NSAttributedString.attributedStringWithAttachment_(attachment)
    return NSAttributedString.alloc().initWithString_(fallback)


def build_menubar_attributed_title(
    cursor_label: str,
    codex_label: str,
    cursor_status: StatusLevel,
    codex_status: StatusLevel,
) -> NSMutableAttributedString:
    font = NSFont.menuBarFontOfSize_(0)
    attributes = {NSFontAttributeName: font}
    result = NSMutableAttributedString.alloc().init()

    def append_text(text: str) -> None:
        part = NSAttributedString.alloc().initWithString_attributes_(text, attributes)
        result.appendAttributedString_(part)

    append_text(f"{STATUS_EMOJI[cursor_status]} ")
    result.appendAttributedString_(_icon_attachment(cursor_icon_path(), "◆"))
    append_text(f" {cursor_label}%   ")
    append_text(f"{STATUS_EMOJI[codex_status]} ")
    result.appendAttributedString_(_icon_attachment(codex_icon_path(), "◈"))
    append_text(f" {codex_label}%")
    return result


def apply_menubar_display(app, state: StateStore) -> None:
    if state.is_unavailable():
        app.title = "⚠ —"
        app.icon = None
        return

    cursor_label = state.menubar_cursor_label()
    codex_label = state.menubar_codex_label()

    try:
        nsitem = app._nsapp.nsstatusitem
        nsitem.setImage_(None)
        nsitem.setTitle_("")
        attributed = build_menubar_attributed_title(
            cursor_label,
            codex_label,
            state.cursor_status_level(),
            state.codex_status_level(),
        )
        button = nsitem.button()
        if button is not None:
            button.setAttributedTitle_(attributed)
            return
    except Exception:  # noqa: BLE001
        pass

    app.title = state.menubar_title_fallback()
