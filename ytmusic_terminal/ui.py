"""Curses-based terminal UI for YouTube Music."""
import curses
import threading
from typing import Optional

from .api import YTMusicAPI
from .player import MPVPlayer

# Color pair IDs
C_HEADER = 1   # white on blue
C_SEARCH = 2   # cyan
C_RESULT = 3   # default
C_SELECT = 4   # bold reverse
C_PLAYING = 5  # yellow
C_PROGRESS = 6 # green
C_STATUS = 7   # red / magenta
C_CONTROLS = 8 # cyan


class App:
    def __init__(self):
        self.api = YTMusicAPI()
        self.player = MPVPlayer()
        self.player.on_end = self._on_track_end

        # UI state
        self.search_query = ""
        self.search_mode = False
        self.results: list[dict] = []
        self.selected = 0
        self.scroll_offset = 0

        # Playback state
        self.queue: list[dict] = []
        self.queue_pos = 0
        self.volume = 100

        self.status = "Press / to search for music"
        self._status_lock = threading.Lock()

    def run(self) -> None:
        curses.wrapper(self._main)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _main(self, stdscr: curses.window) -> None:
        self.stdscr = stdscr
        self._init_colors()
        stdscr.timeout(300)  # 300 ms tick for progress refresh

        while True:
            self._draw()
            key = stdscr.getch()

            if self.search_mode:
                if not self._handle_search_key(key):
                    break
            else:
                if not self._handle_normal_key(key):
                    break

    def _init_colors(self) -> None:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(C_HEADER,   curses.COLOR_WHITE,  curses.COLOR_BLUE)
        curses.init_pair(C_SEARCH,   curses.COLOR_CYAN,   -1)
        curses.init_pair(C_RESULT,   -1,                  -1)
        curses.init_pair(C_PLAYING,  curses.COLOR_YELLOW, -1)
        curses.init_pair(C_PROGRESS, curses.COLOR_GREEN,  -1)
        curses.init_pair(C_STATUS,   curses.COLOR_RED,    -1)
        curses.init_pair(C_CONTROLS, curses.COLOR_CYAN,   -1)

    # ------------------------------------------------------------------
    # Key handlers
    # ------------------------------------------------------------------

    def _handle_search_key(self, key: int) -> bool:
        if key == 27:  # ESC – cancel search
            self.search_mode = False
            self.search_query = ""
        elif key in (curses.KEY_ENTER, 10, 13):
            self._do_search()
            self.search_mode = False
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            self.search_query = self.search_query[:-1]
        elif 32 <= key <= 126:
            self.search_query += chr(key)
        return True

    def _handle_normal_key(self, key: int) -> bool:
        if key == ord("q"):
            self.player.stop()
            return False
        elif key == ord("/"):
            self.search_mode = True
            self.search_query = ""
        elif key in (curses.KEY_UP, ord("k")):
            self._move_selection(-1)
        elif key in (curses.KEY_DOWN, ord("j")):
            self._move_selection(1)
        elif key in (curses.KEY_ENTER, 10, 13):
            self._play_from_selected()
        elif key == ord("p"):
            self.player.pause_resume()
        elif key == ord("n"):
            self._next_track()
        elif key == ord("a"):
            self._add_to_queue()
        elif key == ord("l"):
            self.player.seek(10)
        elif key == ord("h"):
            self.player.seek(-10)
        elif key == ord("+"):
            self.volume = min(150, self.volume + 10)
            self.player.set_volume(self.volume)
        elif key == ord("-"):
            self.volume = max(0, self.volume - 10)
            self.player.set_volume(self.volume)
        return True

    def _move_selection(self, delta: int) -> None:
        if not self.results:
            return
        self.selected = max(0, min(len(self.results) - 1, self.selected + delta))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _do_search(self) -> None:
        query = self.search_query.strip()
        if not query:
            return
        self._set_status(f'Searching for "{query}"…')
        self._draw()
        try:
            tracks = self.api.search_songs(query)
            self.results = tracks
            self.selected = 0
            self.scroll_offset = 0
            if tracks:
                self._set_status(f'Found {len(tracks)} results – Enter to play, a to queue')
            else:
                self._set_status(f'No results for "{query}"')
        except Exception as exc:
            self._set_status(f"Search error: {exc}")

    def _play_from_selected(self) -> None:
        if not self.results or self.selected >= len(self.results):
            return
        self.queue = list(self.results[self.selected:])
        self.queue_pos = 0
        self._play_track(self.queue[0])

    def _add_to_queue(self) -> None:
        if not self.results or self.selected >= len(self.results):
            return
        track = self.results[self.selected]
        self.queue.append(track)
        self._set_status(f'Queued: {track["title"]} – {track["artist"]}')

    def _play_track(self, track: dict) -> None:
        self._set_status(f'Loading: {track["title"]} – {track["artist"]}')
        try:
            self.player.play(track["videoId"], track)
        except RuntimeError as exc:
            self._set_status(str(exc))

    def _next_track(self) -> None:
        if self.queue and self.queue_pos < len(self.queue) - 1:
            self.queue_pos += 1
            self._play_track(self.queue[self.queue_pos])
        else:
            self.player.stop()
            self._set_status("Queue ended – press / to search again")

    def _on_track_end(self) -> None:
        self._next_track()

    def _set_status(self, msg: str) -> None:
        with self._status_lock:
            self.status = msg

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw(self) -> None:
        try:
            self._render()
        except curses.error:
            pass  # ignore transient resize glitches

    def _render(self) -> None:
        h, w = self.stdscr.getmaxyx()
        self.stdscr.erase()

        row = 0

        # ── Header ──────────────────────────────────────────────────────
        title = " YouTube Music Terminal "
        self._addstr(row, 0, title.center(w - 1), curses.color_pair(C_HEADER) | curses.A_BOLD)
        row += 1

        # ── Search bar ──────────────────────────────────────────────────
        if self.search_mode:
            search_line = f" Search: {self.search_query}\u2588"
            curses.curs_set(0)
        else:
            search_line = " Press / to search"
            curses.curs_set(0)
        self._addstr(row, 0, search_line[:w - 1], curses.color_pair(C_SEARCH))
        row += 1
        self._addstr(row, 0, "\u2500" * (w - 1))
        row += 1

        # ── Results list ────────────────────────────────────────────────
        footer_rows = 6  # rows reserved for now-playing + controls
        list_height = max(1, h - row - footer_rows)

        # Adjust scroll so selected stays visible
        if self.selected < self.scroll_offset:
            self.scroll_offset = self.selected
        elif self.selected >= self.scroll_offset + list_height:
            self.scroll_offset = self.selected - list_height + 1

        if not self.results:
            hint = " No results yet – press / to search"
            self._addstr(row, 0, hint[:w - 1])
        else:
            for i in range(list_height):
                idx = i + self.scroll_offset
                if idx >= len(self.results):
                    break
                track = self.results[idx]
                is_current = (
                    self.player.current_track is not None
                    and self.player.current_track.get("videoId") == track.get("videoId")
                )
                line = self._format_track_line(track, w, is_current)
                attr = curses.A_REVERSE if idx == self.selected else 0
                if is_current:
                    attr |= curses.color_pair(C_PLAYING)
                self._addstr(row + i, 0, line, attr)

        row = h - footer_rows

        # ── Divider ─────────────────────────────────────────────────────
        self._addstr(row, 0, "\u2500" * (w - 1))
        row += 1

        # ── Progress bar ────────────────────────────────────────────────
        if self.player.is_playing():
            progress = self.player.get_progress()
            pos = progress.get("position") or 0.0
            dur = progress.get("duration") or 0.0
            paused = progress.get("paused", False)

            if dur > 0:
                bar_width = max(10, w - 18)
                filled = int((pos / dur) * bar_width)
                bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
                pos_s = f"{int(pos // 60):02d}:{int(pos % 60):02d}"
                dur_s = f"{int(dur // 60):02d}:{int(dur % 60):02d}"
                prog_line = f" {pos_s} [{bar}] {dur_s}"
            else:
                prog_line = " Buffering…"
                paused = False

            self._addstr(row, 0, prog_line[:w - 1], curses.color_pair(C_PROGRESS))
            row += 1

            track = self.player.current_track
            if track:
                icon = "\u23f8  " if paused else "\u25b6  "
                np_line = f" {icon}{track['title']} \u2013 {track['artist']}"
                self._addstr(row, 0, np_line[:w - 1], curses.color_pair(C_PLAYING) | curses.A_BOLD)
        else:
            self._addstr(row, 0, " No track playing")
            row += 1
            self._addstr(row, 0, "")
        row += 1

        # ── Status ──────────────────────────────────────────────────────
        with self._status_lock:
            status_msg = self.status
        self._addstr(row, 0, f" {status_msg}"[:w - 1], curses.color_pair(C_STATUS))
        row += 1

        # ── Controls ────────────────────────────────────────────────────
        controls = (
            " [/] Search  [Enter] Play  [p] Pause  [n] Next"
            "  [a] Queue  [h/l] Seek  [+/-] Vol  [q] Quit"
        )
        vol_str = f"Vol:{self.volume}%"
        ctrl_line = controls + "  " + vol_str
        self._addstr(row, 0, ctrl_line[:w - 1], curses.color_pair(C_CONTROLS))

        self.stdscr.refresh()

    def _format_track_line(self, track: dict, width: int, is_current: bool) -> str:
        prefix = "\u25b6 " if is_current else "  "
        left = f"{prefix}{track['title']} \u2013 {track['artist']}"
        right = f"  {track.get('duration', '')} "
        space = width - len(left) - len(right) - 1
        if space < 0:
            left = left[:width - len(right) - 4] + "\u2026"
            space = 0
        return (left + " " * space + right)[:width - 1]

    def _addstr(self, row: int, col: int, text: str, attr: int = 0) -> None:
        h, w = self.stdscr.getmaxyx()
        if row < 0 or row >= h:
            return
        try:
            self.stdscr.addstr(row, col, text[:w - 1], attr)
        except curses.error:
            pass
