from __future__ import annotations

import rumps
from AppKit import (
    NSAttributedString,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSMutableAttributedString,
)

from usage_tracker.icons import claude_icon_path, codex_icon_path, cursor_icon_path
from usage_tracker.models import StatusLevel
from usage_tracker.popover import (
    EMPTY_CHAR,
    FILLED_CHAR,
    METRIC_LINE_RE,
    metric_line_content,
    metric_line_is,
    progress_bar_parts,
    status_level_for,
)


def _noop(_sender) -> None:
    pass


def _append_text(
    result: NSMutableAttributedString,
    text: str,
    font: NSFont,
    color: NSColor,
) -> None:
    if not text:
        return
    part = NSAttributedString.alloc().initWithString_attributes_(
        text,
        {NSFontAttributeName: font, NSForegroundColorAttributeName: color},
    )
    result.appendAttributedString_(part)


def _bar_fill_color(percent: float) -> NSColor:
    level = status_level_for(percent)
    if level == StatusLevel.GREEN:
        return NSColor.systemGreenColor()
    if level == StatusLevel.YELLOW:
        return NSColor.systemYellowColor()
    return NSColor.systemRedColor()


def _menu_text_attributes(*, prominent: bool = False, subtle: bool = False) -> dict:
    if prominent:
        font = NSFont.boldSystemFontOfSize_(13)
        color = NSColor.labelColor()
    elif subtle:
        font = NSFont.systemFontOfSize_(12)
        color = NSColor.secondaryLabelColor()
    else:
        font = NSFont.systemFontOfSize_(13)
        color = NSColor.labelColor()

    return {
        NSFontAttributeName: font,
        NSForegroundColorAttributeName: color,
    }


def styled_menu_item(
    title: str,
    icon_path: str | None = None,
    *,
    prominent: bool = False,
    subtle: bool = False,
) -> rumps.MenuItem:
    item = rumps.MenuItem(title, callback=_noop)
    if icon_path:
        item.icon = icon_path

    attributes = _menu_text_attributes(prominent=prominent, subtle=subtle)
    attributed = NSAttributedString.alloc().initWithString_attributes_(title, attributes)
    item._menuitem.setAttributedTitle_(attributed)
    item._menuitem.setEnabled_(True)
    return item


def styled_metric_menu_item(line: str) -> rumps.MenuItem:
    match = METRIC_LINE_RE.match(line)
    if not match:
        return styled_menu_item(line)

    percent = float(match.group("percent"))
    filled, empty = progress_bar_parts(percent)

    text_font = NSFont.systemFontOfSize_(13)
    bar_font = NSFont.monospacedSystemFontOfSize_weight_(12, 0.5)
    label_color = NSColor.labelColor()
    fill_color = _bar_fill_color(percent)
    empty_color = NSColor.colorWithWhite_alpha_(0.38, 1.0)

    prefix = f"{match.group('prefix')}{match.group('percent')}% "
    suffix = f"  {match.group('suffix')}"
    plain_title = prefix + filled + empty + suffix

    result = NSMutableAttributedString.alloc().init()
    _append_text(result, prefix, text_font, label_color)
    _append_text(result, filled, bar_font, fill_color)
    _append_text(result, empty, bar_font, empty_color)
    _append_text(result, suffix, text_font, label_color)

    item = rumps.MenuItem(plain_title, callback=_noop)
    item._menuitem.setAttributedTitle_(result)
    item._menuitem.setEnabled_(True)
    return item


def styled_metric_menu_item_for_label(label: str, used_percent: float) -> rumps.MenuItem:
    return styled_metric_menu_item(str(metric_line_content(label, used_percent)["plain"]))


def styled_detail_line(line: str) -> rumps.MenuItem:
    if line.startswith("▸"):
        return styled_menu_item(line, prominent=True)
    if line.startswith("   ↳"):
        return styled_menu_item(line, subtle=True)
    if metric_line_is(line):
        return styled_metric_menu_item(line)
    return styled_menu_item(line)


def _summary_item(label: str, icon_path: str | None) -> rumps.MenuItem:
    if metric_line_is(label):
        item = styled_metric_menu_item(label)
        if icon_path:
            item.icon = icon_path
        return item
    return styled_menu_item(label, icon_path)


def summary_cursor_item(label: str) -> rumps.MenuItem:
    return _summary_item(label, cursor_icon_path())


def summary_codex_item(label: str) -> rumps.MenuItem:
    return _summary_item(label, codex_icon_path())


def summary_claude_item(label: str) -> rumps.MenuItem:
    return _summary_item(label, claude_icon_path())
