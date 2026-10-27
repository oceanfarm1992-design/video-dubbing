"""Step 1: get the source video (URL download or local file) and extract its audio."""

import re
from pathlib import Path

from . import DubbingError, run_cmd

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def is_url(source):
    return bool(_URL_RE.match(str(source).strip()))


def download_video(source, out_dir, fmt="bestvideo[height<=1080]+bestaudio/best"):
    """Return a local path to the video. URLs are downloaded with yt-dlp."""
    source = str(source).strip()
    if not is_url(source):
        path = Path(source).expanduser()
        if not path.is_file():
            raise DubbingError(f"Input file not found: {path}")
        return path

    import yt_dlp

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    options = {
        "format": fmt,
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(source, download=True)
            video_id = info.get("id", "")
    except Exception as exc:  # yt-dlp raises many exception types
        raise DubbingError(f"Could not download {source}: {exc}") from exc

    matches = sorted(out_dir.glob(f"{video_id}.*")) if video_id else []
    matches = [m for m in matches if m.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
    if not matches:
        raise DubbingError("Download finished but no video file was found.")
    return matches[0]


def extract_audio(video_path, out_wav, sample_rate=16000):
    """Extract mono 16-bit PCM audio, the format Whisper works best with."""
    out_wav = Path(out_wav)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    run_cmd(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-ac", "1", "-ar", sample_rate,
            "-c:a", "pcm_s16le", out_wav,
        ]
    )
    return out_wav
