#!/bin/sh

set -eu

repository=${FRDLP_REPOSITORY:-nathankaran/yt-dlp_frontend}
source_url=${FRDLP_SOURCE_URL:-https://github.com/${repository}/archive/refs/heads/main.tar.gz}

if [ -n "${FRDLP_PYTHON:-}" ]; then
    python_cmd=$FRDLP_PYTHON
elif command -v python3 >/dev/null 2>&1; then
    python_cmd=python3
elif command -v python >/dev/null 2>&1; then
    python_cmd=python
else
    printf '%s\n' "frdlp requires Python 3.10 or newer." >&2
    exit 1
fi

if ! "$python_cmd" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    printf '%s\n' "frdlp requires Python 3.10 or newer." >&2
    exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
    printf '%s\n' "frdlp requires FFmpeg and ffprobe on PATH." >&2
    printf '%s\n' "Install FFmpeg with your operating system's package manager, then retry." >&2
    exit 1
fi

if [ -n "${XDG_DATA_HOME:-}" ]; then
    data_home=$XDG_DATA_HOME
else
    data_home=$HOME/.local/share
fi

if [ -n "${XDG_BIN_HOME:-}" ]; then
    default_bin_dir=$XDG_BIN_HOME
else
    default_bin_dir=$HOME/.local/bin
fi

install_home=${FRDLP_HOME:-$data_home/frdlp}
bin_dir=${FRDLP_BIN_DIR:-$default_bin_dir}
venv_dir=$install_home/venv
launcher=$bin_dir/frdlp

mkdir -p "$install_home" "$bin_dir"

if [ ! -x "$venv_dir/bin/python" ]; then
    printf '%s\n' "Creating frdlp environment in $venv_dir"
    "$python_cmd" -m venv "$venv_dir"
fi

printf '%s\n' "Installing frdlp from $source_url"
"$venv_dir/bin/python" -m pip install --disable-pip-version-check --upgrade "$source_url"

if [ -e "$launcher" ] && [ ! -L "$launcher" ]; then
    printf '%s\n' "Refusing to replace the existing file at $launcher" >&2
    printf '%s\n' "Set FRDLP_BIN_DIR to choose another command directory." >&2
    exit 1
fi

ln -sfn "$venv_dir/bin/frdlp" "$launcher"

printf '\n%s\n' "frdlp installed successfully: $launcher"
case ":$PATH:" in
    *":$bin_dir:"*)
        printf '%s\n' "Run: frdlp /put/path/here \"video-link\" mp4"
        ;;
    *)
        printf '%s\n' "Add this directory to PATH, then open a new terminal:"
        printf '  export PATH="%s:$PATH"\n' "$bin_dir"
        printf '%s\n' "You can run it now with: $launcher"
        ;;
esac

