"""Windows portable launcher: PlayX.exe (no arguments) opens local DJ Studio."""
import sys
import threading
import webbrowser


def main():
    from playx.cli import main as cli
    if len(sys.argv) == 1:
        sys.argv.append('studio')
        threading.Timer(1.5, lambda: webbrowser.open('http://127.0.0.1:8765')).start()
    cli()


if __name__ == '__main__':
    main()
