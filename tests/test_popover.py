from datetime import datetime, timezone

from usage_tracker.models import AppSnapshot, CodexUsage, CursorUsage
from usage_tracker.popover import (
    build_detail_lines,
    build_detail_text,
    codex_summary_label,
    cursor_summary_label,
    format_codex_five_hour_reset_line,
    format_codex_weekly_reset_line,
    format_cursor_billing_reset_line,
    format_duration,
    format_local_date,
    format_local_time,
    format_metric_line,
    metric_line_content,
    metric_line_is,
    progress_bar,
    progress_bar_parts,
    reset_end_time,
)


def test_format_duration():
    assert format_duration(3661) == "1시간 1분"


def test_progress_bar():
    assert progress_bar(50, width=4) == "██▒▒"


def test_progress_bar():
    assert progress_bar(50, width=4) == "██▒▒"
    filled, empty = progress_bar_parts(50, width=4)
    assert filled + empty == progress_bar(50, width=4)


def test_metric_line_content_matches_format_metric_line():
    plain = format_metric_line("API", 12)
    content = metric_line_content("API", 12)
    assert content["plain"] == plain
    assert content["filled"] + content["empty"] == progress_bar(12)


def test_format_metric_line():
    line = format_metric_line("5시간", 76)
    assert "76%" in line
    assert "24% 남음" in line
    assert "█" in line
    assert metric_line_is(line)


def test_metric_line_is_with_zero_filled_blocks():
    line = format_metric_line("5시간", 1)
    assert "█" not in line
    assert "▒" in line
    assert metric_line_is(line)


def test_summary_labels():
    snapshot = AppSnapshot(
        cursor=CursorUsage(38, 12, datetime(2026, 5, 2, tzinfo=timezone.utc), datetime.now(timezone.utc)),
        codex=CodexUsage(52, 12000, 41, 345600, datetime.now(timezone.utc)),
    )
    assert cursor_summary_label(snapshot) == format_metric_line("Auto+Composer", 38)
    assert codex_summary_label(snapshot) == format_metric_line("5시간", 52)


def test_cursor_billing_reset_line():
    fetched = datetime(2026, 4, 12, 10, 0, tzinfo=timezone.utc)
    billing_end = datetime(2026, 5, 2, 14, 11, 55, tzinfo=timezone.utc)
    line = format_cursor_billing_reset_line(fetched, billing_end)

    assert "후 리셋" in line
    assert "까지" in line
    assert format_local_date(billing_end) in line
    assert "20일" in line


def test_codex_reset_lines_show_end_time_and_date():
    fetched = datetime(2026, 6, 12, 10, 0, tzinfo=timezone.utc)
    five_hour_line = format_codex_five_hour_reset_line(fetched, 3 * 3600 + 22 * 60)
    weekly_line = format_codex_weekly_reset_line(fetched, 4 * 86400 + 8 * 3600)

    assert "3시간 22분 후 리셋" in five_hour_line
    assert "까지" in five_hour_line
    ends_five = reset_end_time(fetched, 3 * 3600 + 22 * 60)
    assert format_local_time(ends_five) in five_hour_line

    assert "4일 8시간 후 리셋" in weekly_line
    ends_week = reset_end_time(fetched, 4 * 86400 + 8 * 3600)
    assert format_local_date(ends_week) in weekly_line


def test_build_detail_lines():
    snapshot = AppSnapshot(
        cursor=CursorUsage(38, 12, datetime(2026, 5, 2, tzinfo=timezone.utc), datetime.now(timezone.utc)),
        codex=CodexUsage(52, 12000, 41, 345600, datetime.now(timezone.utc)),
    )
    lines = build_detail_lines(snapshot, stale=False)

    assert lines[0] == "▸ Cursor Pro+"
    assert any("Auto+Composer" in line for line in lines)
    assert any("5시간" in line for line in lines)
    assert any("갱신" in line for line in lines)


def test_build_detail_text():
    snapshot = AppSnapshot(
        cursor=CursorUsage(38, 12, datetime(2026, 5, 2, tzinfo=timezone.utc), datetime.now(timezone.utc)),
        codex=CodexUsage(52, 12000, 41, 345600, datetime.now(timezone.utc)),
    )
    text = build_detail_text(snapshot, stale=False)

    assert "Cursor Pro+" in text
    assert "Codex Team" in text
