from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from usage_tracker.models import AppSnapshot, StatusLevel

STATUS_EMOJI = {
    StatusLevel.GREEN: "🟢",
    StatusLevel.YELLOW: "🟡",
    StatusLevel.RED: "🔴",
}

WEEKDAYS_KO = ("월", "화", "수", "목", "금", "토", "일")

BAR_WIDTH = 10
FILLED_CHAR = "█"
EMPTY_CHAR = "▒"

METRIC_LINE_RE = re.compile(
    rf"^(?P<prefix>.*?)(?P<percent>\d+)% (?P<bar>[{FILLED_CHAR}{EMPTY_CHAR}]+)  (?P<suffix>\d+% 남음)$"
)


def status_level_for(percent: float) -> StatusLevel:
    return StatusLevel.from_percent(percent)


def format_duration(seconds: int) -> str:
    seconds = max(seconds, 0)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60

    if days:
        if hours:
            return f"{days}일 {hours}시간"
        return f"{days}일"
    if hours and minutes:
        return f"{hours}시간 {minutes}분"
    if hours:
        return f"{hours}시간"
    return f"{minutes}분"


def reset_end_time(fetched_at: datetime, reset_seconds: int) -> datetime:
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    return fetched_at + timedelta(seconds=max(reset_seconds, 0))


def format_local_time(dt: datetime) -> str:
    local = dt.astimezone()
    return local.strftime("%H:%M")


def format_local_date(dt: datetime) -> str:
    local = dt.astimezone()
    weekday = WEEKDAYS_KO[local.weekday()]
    return f"{local.month}/{local.day}({weekday})"


def format_codex_five_hour_reset_line(fetched_at: datetime, reset_seconds: int) -> str:
    ends = reset_end_time(fetched_at, reset_seconds)
    return (
        f"   ↳ {format_duration(reset_seconds)} 후 리셋 · "
        f"{format_local_time(ends)}까지"
    )


def format_codex_weekly_reset_line(fetched_at: datetime, reset_seconds: int) -> str:
    ends = reset_end_time(fetched_at, reset_seconds)
    return (
        f"   ↳ {format_duration(reset_seconds)} 후 리셋 · "
        f"{format_local_date(ends)}까지"
    )


def format_cursor_billing_reset_line(fetched_at: datetime, billing_cycle_end: datetime) -> str:
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    if billing_cycle_end.tzinfo is None:
        billing_cycle_end = billing_cycle_end.replace(tzinfo=timezone.utc)

    remaining_seconds = max(int((billing_cycle_end - fetched_at).total_seconds()), 0)
    return (
        f"   ↳ {format_duration(remaining_seconds)} 후 리셋 · "
        f"{format_local_date(billing_cycle_end)}까지"
    )


def progress_bar_parts(percent: float, width: int = BAR_WIDTH) -> tuple[str, str]:
    filled_count = round(min(max(percent, 0), 100) / 100 * width)
    return FILLED_CHAR * filled_count, EMPTY_CHAR * (width - filled_count)


def progress_bar(percent: float, width: int = BAR_WIDTH) -> str:
    filled, empty = progress_bar_parts(percent, width)
    return filled + empty


def metric_line_content(label: str, used_percent: float) -> dict[str, str | float]:
    emoji = STATUS_EMOJI[status_level_for(used_percent)]
    remaining = max(0, 100 - used_percent)
    filled, empty = progress_bar_parts(used_percent)
    prefix = f"{emoji} {label:<13} {used_percent:3.0f}% "
    suffix = f"  {remaining:.0f}% 남음"
    return {
        "plain": prefix + filled + empty + suffix,
        "prefix": prefix,
        "filled": filled,
        "empty": empty,
        "suffix": suffix,
        "percent": used_percent,
    }


def format_metric_line(label: str, used_percent: float) -> str:
    return str(metric_line_content(label, used_percent)["plain"])


def metric_line_is(line: str) -> bool:
    return METRIC_LINE_RE.match(line) is not None


def cursor_summary_label(snapshot: AppSnapshot) -> str:
    if snapshot.cursor and not snapshot.cursor.error:
        return format_metric_line("Auto+Composer", snapshot.cursor.auto_percent)
    if snapshot.cursor and snapshot.cursor.error:
        return "⚠  조회 실패"
    return "—"


def codex_summary_label(snapshot: AppSnapshot) -> str:
    if snapshot.codex and not snapshot.codex.error:
        return format_metric_line("5시간", snapshot.codex.five_hour_used_percent)
    if snapshot.codex and snapshot.codex.error:
        return "⚠  조회 실패"
    return "—"


def format_updated_at(snapshot: AppSnapshot, stale: bool) -> str:
    latest: datetime | None = None
    for usage in (snapshot.cursor, snapshot.codex):
        if usage and not usage.error:
            if latest is None or usage.fetched_at > latest:
                latest = usage.fetched_at
    if latest is None:
        return "갱신 정보 없음"
    seconds = int((datetime.now(timezone.utc) - latest).total_seconds())
    if seconds < 5:
        text = "방금 갱신됨"
    elif seconds < 60:
        text = f"{seconds}초 전 갱신"
    else:
        text = f"{seconds // 60}분 전 갱신"
    if stale:
        text += "  ⚠"
    return text


def build_detail_lines(snapshot: AppSnapshot, stale: bool) -> list[str]:
    lines: list[str] = ["▸ Cursor Pro+"]

    if snapshot.cursor and not snapshot.cursor.error:
        c = snapshot.cursor
        lines.append(format_metric_line("Auto+Composer", c.auto_percent))
        lines.append(format_metric_line("API", c.api_percent))
        lines.append(format_cursor_billing_reset_line(c.fetched_at, c.billing_cycle_end))
    elif snapshot.cursor and snapshot.cursor.error:
        lines.append(f"   ⚠ {snapshot.cursor.error}")
    else:
        lines.append("   데이터 없음")

    lines.extend(["", "▸ Codex Team"])

    if snapshot.codex and not snapshot.codex.error:
        x = snapshot.codex
        lines.append(format_metric_line("5시간", x.five_hour_used_percent))
        lines.append(format_codex_five_hour_reset_line(x.fetched_at, x.five_hour_reset_seconds))
        lines.append(format_metric_line("1주", x.seven_day_used_percent))
        lines.append(format_codex_weekly_reset_line(x.fetched_at, x.seven_day_reset_seconds))
    elif snapshot.codex and snapshot.codex.error:
        lines.append(f"   ⚠ {snapshot.codex.error}")
    else:
        lines.append("   데이터 없음")

    lines.extend(["", format_updated_at(snapshot, stale)])
    return lines


def build_detail_text(snapshot: AppSnapshot, stale: bool) -> str:
    return "\n".join(build_detail_lines(snapshot, stale))
