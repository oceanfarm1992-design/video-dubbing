#!/usr/bin/env bash
# Creates a virtual environment and installs everything needed to run the dubber.
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found." >&2
  exit 1
fi

for tool in ffmpeg ffprobe; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "$tool is required but was not found on PATH." >&2
    echo "  macOS:   brew install ffmpeg" >&2
    echo "  Ubuntu:  sudo apt-get install ffmpeg" >&2
    echo "  Windows: winget install ffmpeg" >&2
    exit 1
  fi
done

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

mkdir -p workspace output

echo
echo "Setup complete. Activate the environment with:"
echo "  source .venv/bin/activate"
echo "Then try:"
echo "  python cli.py path/to/video.mp4"
echo "  python app.py"
