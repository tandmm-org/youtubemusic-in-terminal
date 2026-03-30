"""MPV-based audio player with IPC control."""
import json
import os
import socket
import subprocess
import tempfile
import threading
import time
from typing import Callable, Optional


class MPVPlayer:
    """Plays audio via mpv using a Unix IPC socket for control."""

    SOCKET_PATH = os.path.join(tempfile.gettempdir(), "ytmusic_mpv.sock")

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self.current_track: Optional[dict] = None
        self.on_end: Optional[Callable] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def play(self, video_id: str, track: dict) -> None:
        """Start playing the given YouTube Music video ID."""
        self.stop()
        self.current_track = track
        url = f"https://music.youtube.com/watch?v={video_id}"
        cmd = [
            "mpv",
            "--no-video",
            "--really-quiet",
            f"--input-ipc-server={self.SOCKET_PATH}",
            "--ytdl-format=bestaudio/best",
            url,
        ]
        try:
            self._process = subprocess.Popen(cmd)
        except FileNotFoundError:
            raise RuntimeError(
                "mpv not found. Install it with: sudo apt install mpv"
            )
        threading.Thread(target=self._monitor, daemon=True).start()

    def pause_resume(self) -> None:
        self._send("cycle", "pause")

    def seek(self, seconds: float) -> None:
        self._send("seek", seconds, "relative")

    def set_volume(self, volume: int) -> None:
        self._send("set_property", "volume", max(0, min(150, volume)))

    def stop(self) -> None:
        with self._lock:
            if self._process and self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()
            self._process = None
            self.current_track = None
            self._cleanup_socket()

    def is_playing(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def get_progress(self) -> dict:
        """Return dict with optional keys: position, duration, paused."""
        result = {}
        pos = self._get_property("time-pos")
        if pos is not None:
            result["position"] = pos
        dur = self._get_property("duration")
        if dur is not None:
            result["duration"] = dur
        paused = self._get_property("pause")
        if paused is not None:
            result["paused"] = paused
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _monitor(self) -> None:
        if self._process:
            self._process.wait()
            if self.on_end and self._process is not None and self._process.returncode == 0:
                self.on_end()

    def _send(self, *args) -> Optional[dict]:
        """Send an IPC command to mpv. Retries briefly if socket not ready."""
        for _ in range(5):
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    s.connect(self.SOCKET_PATH)
                    payload = json.dumps({"command": list(args)}) + "\n"
                    s.sendall(payload.encode())
                    raw = s.recv(4096).decode(errors="replace")
                    return json.loads(raw)
            except (FileNotFoundError, ConnectionRefusedError, OSError):
                time.sleep(0.3)
            except (json.JSONDecodeError, socket.timeout):
                return None
        return None

    def _get_property(self, name: str):
        resp = self._send("get_property", name)
        if resp and resp.get("error") == "success":
            return resp.get("data")
        return None

    def _cleanup_socket(self) -> None:
        try:
            os.remove(self.SOCKET_PATH)
        except FileNotFoundError:
            pass
