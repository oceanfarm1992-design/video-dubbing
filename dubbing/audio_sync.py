"""Step 5: fit each Tamil clip into its time slot and lay them on one timeline."""

import logging
from pathlib import Path

from . import DubbingError, media_duration, run_cmd

log = logging.getLogger(__name__)


def fit_clip(src, dst, target_duration, sample_rate=44100, max_speedup=1.6):
    """Convert `src` to wav, speeding it up (never slowing it down) to fit `target_duration`.

    Returns the resulting clip duration in seconds.
    """
    duration = media_duration(src)
    if target_duration <= 0 or duration <= target_duration:
        run_cmd(["ffmpeg", "-y", "-i", src, "-ar", sample_rate, "-ac", "1", dst])
        return duration

    # ffmpeg's atempo filter accepts 0.5 to 2.0 in a single stage.
    factor = min(duration / target_duration, max_speedup, 2.0)
    run_cmd(
        [
            "ffmpeg", "-y", "-i", src,
            "-filter:a", f"atempo={factor:.4f}",
            "-ar", sample_rate, "-ac", "1", dst,
        ]
    )
    return duration / factor


def build_dub_track(
    segments,
    clips,
    total_duration,
    out_wav,
    work_dir,
    sample_rate=44100,
    max_speedup=1.6,
    gap=0.1,
):
    """Lay every clip on one track and export a wav. Speech is never cut off.

    Each clip is sped up (up to `max_speedup`) to finish before the next segment.
    If it still runs long, the following clips start later instead of overlapping,
    and the track grows past `total_duration` when the last clip ends after the video.
    """
    try:
        from pydub import AudioSegment
    except ImportError as exc:
        raise DubbingError(
            "pydub is not installed. Run: pip install -r requirements.txt"
        ) from exc

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    placed = []  # (position in ms, audio)
    cursor = 0.0  # earliest time the next clip may start
    for index, (seg, clip) in enumerate(zip(segments, clips)):
        if clip is None:
            continue

        start = max(seg.start, cursor)
        next_start = segments[index + 1].start if index + 1 < len(segments) else total_duration
        target = max(next_start - start - gap, 0.3)

        fitted = work_dir / f"fit_{index:04d}.wav"
        fit_clip(clip, fitted, target, sample_rate, max_speedup)
        audio = AudioSegment.from_wav(str(fitted))

        if start - seg.start > 0.05:
            log.warning("Segment %d starts %.1fs late so earlier speech is not cut off.",
                        index, start - seg.start)
        placed.append((int(start * 1000), audio))
        cursor = start + len(audio) / 1000 + gap

    total_ms = max([int(total_duration * 1000)] + [pos + len(audio) for pos, audio in placed])
    track = AudioSegment.silent(duration=total_ms, frame_rate=sample_rate).set_channels(1)
    for position, audio in placed:
        track = track.overlay(audio, position=position)

    track.export(str(out_wav), format="wav")
    return Path(out_wav)
