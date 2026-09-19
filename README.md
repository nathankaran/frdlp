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

## Quick install

The installer checks for Python and FFmpeg, creates an isolated environment in
your user account, and installs or upgrades `frdlp` from this GitHub repository.
It does not require `pipx` or administrator access.

### Linux and macOS

```console
curl -fsSL https://raw.githubusercontent.com/nathankaran/yt-dlp_frontend/main/install.sh | sh
```

The command is linked into `~/.local/bin`. If that directory is not already on
`PATH`, the installer prints the one-line command needed to add it.

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/nathankaran/yt-dlp_frontend/main/install.ps1 | iex
```

The PowerShell installer adds its command directory to your user `PATH`; open a
new terminal afterward.

Both commands install the current `main` branch and can be rerun to upgrade.
To inspect an installer before running it, open [install.sh](install.sh) or
[install.ps1](install.ps1).

### Local or development install

From a local checkout, you can still install into an active virtual environment:

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
