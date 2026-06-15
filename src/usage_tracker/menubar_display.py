from __future__ import annotations

from AppKit import (
    NSAttributedString,
    NSFont,
    NSFontAttributeName,
    NSMutableAttributedString,
    NSTextAttachment,
)

from usage_tracker.icons import claude_icon_path, codex_icon_path, cursor_icon_path
from usage_tracker.state import STATUS_EMOJI, MenubarEntry, StateStore

ICON_SIZE = 14.0

SERVICE_ICONS = {
    "cursor": (cursor_icon_path, "◆"),
    "codex": (codex_icon_path, "◈"),
    "claude": (claude_icon_path, "◇"),
}


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


def build_menubar_attributed_title(entries: list[MenubarEntry]) -> NSMutableAttributedString:
    font = NSFont.menuBarFontOfSize_(0)
    attributes = {NSFontAttributeName: font}
    result = NSMutableAttributedString.alloc().init()

    def append_text(text: str) -> None:
        part = NSAttributedString.alloc().initWithString_attributes_(text, attributes)
        result.appendAttributedString_(part)

    for index, entry in enumerate(entries):
        if index > 0:
            append_text("   ")
        icon_fn, fallback = SERVICE_ICONS[entry.service]
        append_text(f"{STATUS_EMOJI[entry.status]} ")
        result.appendAttributedString_(_icon_attachment(icon_fn(), fallback))
        append_text(f" {entry.label}%")
    return result


def apply_menubar_display(app, state: StateStore) -> None:
    entries = state.menubar_entries()
    if not entries:
        app.title = "⚠ —"
        app.icon = None
        return

    try:
        nsitem = app._nsapp.nsstatusitem
        nsitem.setImage_(None)
        nsitem.setTitle_("")
        attributed = build_menubar_attributed_title(entries)
        button = nsitem.button()
        if button is not None:
            button.setAttributedTitle_(attributed)
            return
    except Exception:  # noqa: BLE001
        pass

    app.title = state.menubar_title_fallback()
