"""Entry point for `python -m ytmusic_terminal` and the `ytmusic` CLI command."""
import sys


def main() -> None:
    try:
        from .ui import App
    except ImportError as exc:
        print(f"Missing dependency: {exc}")
        print("Run:  pip install -r requirements.txt")
        sys.exit(1)

    app = App()
    try:
        app.run()
    except KeyboardInterrupt:
        app.player.stop()


if __name__ == "__main__":
    main()
