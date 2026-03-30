# YouTube Music Terminal

A keyboard-driven terminal client for YouTube Music. Search for songs, play audio, manage a queue, and control playback — all without leaving the terminal.

## Requirements

- Python 3.9+
- [mpv](https://mpv.io/) with yt-dlp support

Install system dependencies (Debian/Ubuntu):

```bash
sudo apt install mpv
```

## Installation

```bash
git clone https://github.com/tandmm-org/youtubemusic-in-terminal.git
cd youtubemusic-in-terminal
pip install -e .
```

Or install dependencies directly without packaging:

```bash
pip install -r requirements.txt
```

## Usage

```bash
ytmusic
# or
python -m ytmusic_terminal
```

## Interface

```
┌─ YouTube Music Terminal ──────────────────────────────────────┐
│ Press / to search                                             │
├───────────────────────────────────────────────────────────────┤
│ ▶ Blinding Lights – The Weeknd                        3:20   │
│   Save Your Tears – The Weeknd                        3:35   │
│   Starboy – The Weeknd                                3:50   │
│   ...                                                        │
├───────────────────────────────────────────────────────────────┤
│ 01:23 [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 03:20    │
│ ▶  Blinding Lights – The Weeknd                              │
│ Search error / status messages appear here                   │
│ [/] Search  [Enter] Play  [p] Pause  [n] Next  [q] Quit ...  │
└───────────────────────────────────────────────────────────────┘
```

## Keyboard Controls

| Key | Action |
|-----|--------|
| `/` | Open search |
| `Enter` | Play selected track (queues rest of results) |
| `↑` / `k` | Move selection up |
| `↓` / `j` | Move selection down |
| `p` | Pause / resume |
| `n` | Skip to next track |
| `a` | Add selected track to queue |
| `h` | Seek back 10 seconds |
| `l` | Seek forward 10 seconds |
| `+` | Volume up |
| `-` | Volume down |
| `Esc` | Cancel search input |
| `q` | Quit |

## How It Works

- **Search** — uses [`ytmusicapi`](https://ytmusicapi.readthedocs.io/) (no login required for search)
- **Playback** — streams audio via `mpv` using yt-dlp as the backend (`--ytdl-format=bestaudio/best`)
- **Control** — communicates with the running `mpv` process over a Unix IPC socket for pause, seek, and volume changes
- **UI** — built with Python's standard `curses` library; refreshes every 300 ms for the progress bar

## Project Structure

```
ytmusic_terminal/
├── __init__.py      version
├── __main__.py      entry point
├── api.py           YouTube Music search (ytmusicapi)
├── player.py        MPV audio player with IPC socket control
└── ui.py            Curses terminal UI
```
