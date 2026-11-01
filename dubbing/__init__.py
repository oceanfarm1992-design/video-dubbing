"""English to Tamil video dubbing pipeline.

This module only holds small shared helpers. Heavy dependencies are imported
lazily inside the submodules so the package imports quickly.
"""

import subprocess

__version__ = "0.1.0"


class DubbingError(RuntimeError):
    """Raised when a pipeline step fails in a way the user can act on."""


def run_cmd(cmd):
    """Run an external command and return its stdout, raising DubbingError on failure."""
    args = [str(part) for part in cmd]
    try:
        proc = subprocess.run(args, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise DubbingError(
            f"Command not found: {args[0]}. Is it installed and on your PATH?"
        ) from exc
    if proc.returncode != 0:
        raise DubbingError(
            f"{args[0]} failed (exit {proc.returncode}):\n{proc.stderr[-2000:]}"
        )
    return proc.stdout


def media_duration(path):
    """Duration of an audio or video file in seconds."""
    out = run_cmd(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ]
    )
    return float(out.strip())


def video_codec(path):
    """Codec name of the first video stream, e.g. 'h264' or 'av1'."""
    out = run_cmd(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name",
            "-of", "csv=p=0",
            path,
        ]
    )
    return out.strip()


def has_audio_stream(path):
    """True if the file contains at least one audio stream."""
    out = run_cmd(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=index",
            "-of", "csv=p=0",
            path,
        ]
    )
    return bool(out.strip())
