"""Events passed from the yt-dlp worker to the terminal UI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EventKind(str, Enum):
    STAGE = "stage"
    PROGRESS = "progress"
    LOG = "log"
    OUTPUT = "output"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class DownloadEvent:
    kind: EventKind
    message: str = ""
    title: str = ""
    filename: str = ""
    stage: str = ""
    downloaded_bytes: int | None = None
    total_bytes: int | None = None
    speed: float | None = None
    eta: float | None = None
    playlist_index: int | None = None
    playlist_count: int | None = None
    final_paths: tuple[str, ...] = ()

