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
    max_overflow=1.4,
):
    """Place every clip at its segment start on a silent track and export a wav."""
    try:
        from pydub import AudioSegment
    except ImportError as exc:
        raise DubbingError(
            "pydub is not installed. Run: pip install -r requirements.txt"
        ) from exc

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    total_ms = int(total_duration * 1000)
    track = AudioSegment.silent(duration=total_ms, frame_rate=sample_rate).set_channels(1)

    for index, (seg, clip) in enumerate(zip(segments, clips)):
        if clip is None:
            continue

        slot = max(seg.end - seg.start, 0.3)
        next_start = segments[index + 1].start if index + 1 < len(segments) else total_duration
        available = max(next_start - seg.start - 0.05, slot)
        # Let a clip use the silence after its segment, but not more than max_overflow x its slot.
        target = min(available, max(slot, slot * max_overflow))

        fitted = work_dir / f"fit_{index:04d}.wav"
        fit_clip(clip, fitted, target, sample_rate, max_speedup)
        audio = AudioSegment.from_wav(str(fitted))

        limit_ms = int(available * 1000)
        if len(audio) > limit_ms:
            log.warning("Segment %d is still too long after speed-up; trimming the end.", index)
            audio = audio[:limit_ms].fade_out(80)

        track = track.overlay(audio, position=int(seg.start * 1000))

    track.export(str(out_wav), format="wav")
    return Path(out_wav)
