"""Command-line entry point for frdlp."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys
from collections.abc import Sequence

from frdlp import __version__
from frdlp.presets import FormatPreset, PRESETS, parse_preset


def _preset_argument(value: str) -> FormatPreset:
    try:
        return parse_preset(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="frdlp",
        description="Download a video or playlist in a live terminal dashboard.",
        epilog="filetypes: " + ", ".join(PRESETS),
    )
    parser.add_argument("destination", help="directory in which downloads are saved")
    parser.add_argument("url", help="video or playlist URL understood by yt-dlp")
    parser.add_argument("filetype", type=_preset_argument, metavar="FILETYPE")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def prepare_destination(value: str) -> Path:
    """Resolve and create the requested destination, or raise ValueError."""
    destination = Path(value).expanduser()
    try:
        destination.mkdir(parents=True, exist_ok=True)
        destination = destination.resolve()
    except OSError as error:
        raise ValueError(f"cannot create destination {value!r}: {error}") from error

    if not destination.is_dir():
        raise ValueError(f"destination is not a directory: {destination}")
    if not os.access(destination, os.W_OK | os.X_OK):
        raise ValueError(f"destination is not writable: {destination}")
    return destination


def terminal_is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        destination = prepare_destination(args.destination)
    except ValueError as error:
        parser.print_usage(sys.stderr)
        print(f"frdlp: error: {error}", file=sys.stderr)
        return 2

    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        print(
            "frdlp: error: FFmpeg and ffprobe must be installed and available on PATH.",
            file=sys.stderr,
        )
        return 2

    if not terminal_is_interactive():
        print(
            "frdlp: error: an interactive terminal is required for the download dashboard.",
            file=sys.stderr,
        )
        return 2

    try:
        from frdlp.app import DownloadApp
    except ImportError as error:
        print(f"frdlp: error: unable to load the terminal UI: {error}", file=sys.stderr)
        return 2

    result = DownloadApp(destination, args.url, args.filetype).run()
    return int(result) if result is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
