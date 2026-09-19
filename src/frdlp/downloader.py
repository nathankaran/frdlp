"""yt-dlp integration kept independent from the Textual application."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from threading import Event
from typing import Any, Protocol

from frdlp.events import DownloadEvent, EventKind
from frdlp.presets import FormatPreset


# The `playlist` field is playlist_title with playlist_id as its fallback.
# A single video uses `.` so the path remains relative to the configured home
# directory; yt-dlp would treat an empty first component as an absolute path.
OUTPUT_TEMPLATE = "%(playlist|.)s/%(title)s [%(id)s].%(ext)s"


class YoutubeDLFactory(Protocol):
    def __call__(self, options: Mapping[str, Any]) -> Any: ...


class DownloadCancelled(Exception):
    """Raised from a yt-dlp hook at a safe cancellation point."""


class EventLogger:
    """Adapt yt-dlp logger messages to download events."""

    def __init__(self, emit: Callable[[DownloadEvent], None]) -> None:
        self._emit = emit

    def debug(self, message: str) -> None:
        # yt-dlp sends ordinary informational output through debug() when a
        # custom logger is installed. Only the explicit debug prefix is noisy.
        if not message.startswith("[debug] "):
            self._log(message)

    def info(self, message: str) -> None:
        self._log(message)

    def warning(self, message: str) -> None:
        self._log(f"Warning: {message}")

    def error(self, message: str) -> None:
        self._log(message)

    def _log(self, message: str) -> None:
        message = message.strip()
        if message:
            self._emit(DownloadEvent(EventKind.LOG, message=message))


def build_ydl_options(
    destination: Path,
    preset: FormatPreset,
    progress_hook: Callable[[dict[str, Any]], None],
    postprocessor_hook: Callable[[dict[str, Any]], None],
    post_hook: Callable[[str], None],
    logger: EventLogger,
) -> dict[str, Any]:
    """Build the complete, intentionally small yt-dlp API configuration."""
    options: dict[str, Any] = {
        "paths": {"home": str(destination)},
        "outtmpl": {"default": OUTPUT_TEMPLATE},
        "progress_hooks": [progress_hook],
        "postprocessor_hooks": [postprocessor_hook],
        "post_hooks": [post_hook],
        "logger": logger,
        "quiet": True,
        "no_warnings": False,
        "ignoreerrors": False,
        "continuedl": True,
        "nopart": False,
        "overwrites": False,
    }
    options.update(preset.ydl_options())
    return options


class YtDlpRunner:
    """Execute one URL and emit typed events for the UI."""

    def __init__(
        self,
        destination: Path,
        url: str,
        preset: FormatPreset,
        cancel_event: Event,
        emit: Callable[[DownloadEvent], None],
        ydl_factory: YoutubeDLFactory | None = None,
    ) -> None:
        self.destination = destination
        self.url = url
        self.preset = preset
        self.cancel_event = cancel_event
        self.emit = emit
        self._ydl_factory = ydl_factory
        self._final_paths: list[str] = []

    def run(self) -> None:
        self.emit(DownloadEvent(EventKind.STAGE, stage="Starting"))
        logger = EventLogger(self.emit)
        options = build_ydl_options(
            self.destination,
            self.preset,
            self._progress_hook,
            self._postprocessor_hook,
            self._post_hook,
            logger,
        )

        try:
            factory = self._ydl_factory
            if factory is None:
                from yt_dlp import YoutubeDL

                factory = YoutubeDL
            with factory(options) as ydl:
                result = ydl.download([self.url])
            if self.cancel_event.is_set():
                raise DownloadCancelled
            if result:
                raise RuntimeError(f"yt-dlp exited with status {result}")
        except BaseException as error:
            if self.cancel_event.is_set() or isinstance(error, DownloadCancelled):
                self.emit(
                    DownloadEvent(
                        EventKind.CANCELLED,
                        message="Download cancelled; partial files were kept for resuming.",
                    )
                )
                return
            if isinstance(error, KeyboardInterrupt):
                raise
            message = str(error).strip() or error.__class__.__name__
            self.emit(DownloadEvent(EventKind.ERROR, message=message))
            return

        paths = tuple(dict.fromkeys(self._final_paths))
        self.emit(
            DownloadEvent(
                EventKind.COMPLETE,
                message="Download complete.",
                final_paths=paths,
            )
        )

    def _check_cancelled(self) -> None:
        if self.cancel_event.is_set():
            raise DownloadCancelled

    def _progress_hook(self, data: dict[str, Any]) -> None:
        self._check_cancelled()
        status = data.get("status")
        info = data.get("info_dict") or {}
        common = self._common_fields(info)

        if status == "downloading":
            total = _as_int(data.get("total_bytes")) or _as_int(
                data.get("total_bytes_estimate")
            )
            self.emit(
                DownloadEvent(
                    EventKind.PROGRESS,
                    stage="Downloading",
                    filename=str(data.get("filename") or info.get("filepath") or ""),
                    downloaded_bytes=_as_int(data.get("downloaded_bytes")),
                    total_bytes=total,
                    speed=_as_float(data.get("speed")),
                    eta=_as_float(data.get("eta")),
                    **common,
                )
            )
        elif status == "finished":
            self.emit(
                DownloadEvent(
                    EventKind.PROGRESS,
                    stage="Preparing post-processing",
                    filename=str(data.get("filename") or info.get("filepath") or ""),
                    downloaded_bytes=_as_int(data.get("downloaded_bytes")),
                    total_bytes=_as_int(data.get("total_bytes")),
                    **common,
                )
            )

    def _postprocessor_hook(self, data: dict[str, Any]) -> None:
        self._check_cancelled()
        info = data.get("info_dict") or {}
        processor = str(data.get("postprocessor") or "Post-processing")
        status = str(data.get("status") or "working")
        self.emit(
            DownloadEvent(
                EventKind.STAGE,
                stage=f"{processor}: {status}",
                filename=str(info.get("filepath") or ""),
                **self._common_fields(info),
            )
        )

    def _post_hook(self, filename: str) -> None:
        path = str(filename)
        if path and path not in self._final_paths:
            self._final_paths.append(path)
        self.emit(DownloadEvent(EventKind.OUTPUT, filename=path))

    @staticmethod
    def _common_fields(info: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "title": str(info.get("title") or ""),
            "playlist_index": _as_int(info.get("playlist_index")),
            "playlist_count": _as_int(
                info.get("playlist_count") or info.get("n_entries")
            ),
        }


def _as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
