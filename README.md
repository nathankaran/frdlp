# frdlp

`frdlp` is a small terminal dashboard for downloading a video or playlist with
[yt-dlp](https://github.com/yt-dlp/yt-dlp).

```console
frdlp /put/path/here "https://example.com/video" mp4
```

The dashboard shows the current title, file, download progress, speed, ETA,
playlist position, post-processing stage, and recent yt-dlp messages. A single
video is saved directly in the destination. A playlist is saved in a child
directory named after the playlist (falling back to its ID).

## Requirements

- Python 3.10 or newer
- [FFmpeg](https://ffmpeg.org/) available on `PATH`
- An interactive terminal

## Install

From this directory, the recommended installation is:

```console
pipx install .
```

You can also install it in an active virtual environment:

```console
python -m pip install .
```

For development and tests:

```console
python -m pip install -e '.[test]'
pytest
```

## Usage

```text
frdlp DESTINATION URL FILETYPE
```

`FILETYPE` is case-insensitive and accepts:

- `best` — best video and audio, preserving yt-dlp's selected container
- `audio` — best audio stream in its native format
- `mp4`, `webm`, `mkv`, `mov` — best source converted or remuxed to that type
- `mp3`, `m4a`, `wav`, `flac`, `opus` — best audio converted to that type

Explicit extensions are guaranteed through FFmpeg conversion when necessary.
Completed files follow yt-dlp's normal no-overwrite behavior, while partial
downloads remain available for resuming. During a download, press `q` or
Ctrl+C and confirm to cancel. On completion, press Enter or `q` to exit.

Advanced yt-dlp flags, cookies, authentication, subtitles, and metadata or
thumbnail embedding are intentionally outside the first release.

# yt-dlp_frontend
