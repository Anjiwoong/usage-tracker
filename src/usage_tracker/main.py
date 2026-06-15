from __future__ import annotations

import concurrent.futures

import rumps

from usage_tracker.alerts import AlertService
from usage_tracker.claude_fetcher import ClaudeFetcher
from usage_tracker.codex_fetcher import CodexFetcher
from usage_tracker.config import load_config
from usage_tracker.cursor_fetcher import CursorFetcher
from usage_tracker.menubar_display import apply_menubar_display
from usage_tracker.menu_style import (
    styled_detail_line,
    summary_claude_item,
    summary_codex_item,
    summary_cursor_item,
)
from usage_tracker.popover import (
    build_detail_lines,
    claude_summary_label,
    codex_summary_label,
    cursor_summary_label,
)
from usage_tracker.state import StateStore


class UsageTrackerApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("Usage", quit_button=None)
        self.config = load_config()
        self.state = StateStore()
        self.cursor_fetcher = CursorFetcher(self.config.cursor_session_token)
        self.codex_fetcher = CodexFetcher()
        self.claude_fetcher = ClaudeFetcher()
        self.alerts = AlertService(notify=self._send_notification)

        self._refresh_item = rumps.MenuItem("↻  지금 새로고침", callback=self.refresh_now)
        self._settings_item = rumps.MenuItem("⚙  설정 안내", callback=self.show_settings_help)
        self._quit_item = rumps.MenuItem("종료", callback=self.quit_app)

        self.timer = rumps.Timer(self.poll, self.config.poll_interval_seconds)
        self.timer.start()
        self.poll(None)

    def _send_notification(self, service: str, percent: float, threshold: int) -> None:
        if threshold >= 100:
            title = f"{service} 한도 소진"
            message = "포함 사용량을 모두 사용했습니다."
        else:
            title = f"{service} 사용량 {threshold}% 도달"
            message = f"현재 {percent:.0f}% 사용 중입니다."
        rumps.notification(
            title=title,
            subtitle=message,
            message="한도를 확인하세요.",
        )

    def _render_detail_menu(self) -> None:
        snapshot = self.state.snapshot()
        stale = self.state.is_stale()
        lines = build_detail_lines(snapshot, stale)

        menu_items: list[rumps.MenuItem | None] = [
            summary_cursor_item(cursor_summary_label(snapshot)),
            summary_codex_item(codex_summary_label(snapshot)),
            summary_claude_item(claude_summary_label(snapshot)),
            None,
        ]

        for line in lines:
            if line == "":
                menu_items.append(None)
            else:
                menu_items.append(styled_detail_line(line))

        menu_items.extend([
            None,
            self._refresh_item,
            self._settings_item,
            None,
            self._quit_item,
        ])

        self.menu.clear()
        self.menu.update(menu_items)

    def poll(self, _sender) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            cursor_future = pool.submit(self.cursor_fetcher.fetch)
            codex_future = pool.submit(self.codex_fetcher.fetch)
            claude_future = pool.submit(self.claude_fetcher.fetch)
            cursor = cursor_future.result()
            codex = codex_future.result()
            claude = claude_future.result()

        self.state.update(cursor=cursor, codex=codex, claude=claude)
        self.alerts.check(cursor, codex, claude)
        apply_menubar_display(self, self.state)
        self._render_detail_menu()

    @rumps.clicked("↻  지금 새로고침")
    def refresh_now(self, _sender) -> None:
        self.poll(None)

    @rumps.clicked("⚙  설정 안내")
    def show_settings_help(self, _sender) -> None:
        rumps.alert(
            title="설정 안내",
            message=(
                "Cursor:\n"
                "1. cursor.com/dashboard/usage 접속\n"
                "2. DevTools → Cookies → WorkosCursorSessionToken 복사\n"
                "3. .env에 CURSOR_SESSION_TOKEN=... 저장\n\n"
                "Codex: codex login으로 인증되어 있으면 추가 설정 불필요\n\n"
                "Claude: claude login으로 인증되어 있으면 추가 설정 불필요"
            ),
        )

    @rumps.clicked("종료")
    def quit_app(self, _sender) -> None:
        rumps.quit_application()


def main() -> None:
    UsageTrackerApp().run()


if __name__ == "__main__":
    main()
