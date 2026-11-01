"""Step 6: write subtitles and mux the dubbed audio back into the video."""

from pathlib import Path

from . import has_audio_stream, media_duration, run_cmd, video_codec


def _srt_time(seconds):
    millis = int(round(seconds * 1000))
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(segments, out_path):
    """Write the Tamil translations as an .srt subtitle file."""
    lines = []
    shown = [seg for seg in segments if seg.translation.strip()]
    for number, seg in enumerate(shown, start=1):
        lines.append(str(number))
        lines.append(f"{_srt_time(seg.start)} --> {_srt_time(seg.end)}")
        lines.append(seg.translation.strip())
        lines.append("")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def merge(
    video_path,
    dub_wav,
    out_path,
    keep_original_audio=False,
    original_volume=0.08,
    dubbed_volume=1.0,
    srt_path=None,
):
    """Combine the original video stream with the dubbed track into an mp4.

    The video is re-encoded to H.264 unless it already is, so the result plays on
    every phone and player. If the dub runs past the end of the video, the last
    frame is held until the speech finishes.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    extra = media_duration(dub_wav) - media_duration(video_path)
    pad = extra if extra > 0.05 else 0.0
    if pad == 0.0 and video_codec(video_path) == "h264":
        video_args = ["-c:v", "copy"]
    else:
        video_args = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]
        if pad:
            video_args += ["-filter:v", f"tpad=stop_mode=clone:stop_duration={pad:.3f}"]

    cmd = ["ffmpeg", "-y", "-i", video_path, "-i", dub_wav]
    if srt_path:
        cmd += ["-i", srt_path]

    mix_original = keep_original_audio and has_audio_stream(video_path)
    if mix_original:
        graph = (
            f"[0:a]volume={original_volume}[bg];"
            f"[1:a]volume={dubbed_volume}[fg];"
            "[bg][fg]amix=inputs=2:duration=longest:dropout_transition=0,volume=2[a]"
        )
        cmd += ["-filter_complex", graph, "-map", "0:v:0", "-map", "[a]"]
    else:
        cmd += ["-filter:a", f"volume={dubbed_volume}", "-map", "0:v:0", "-map", "1:a:0"]

    if srt_path:
        cmd += ["-map", "2:0", "-c:s", "mov_text", "-metadata:s:s:0", "language=tam"]

    cmd += video_args + ["-c:a", "aac", "-b:a", "192k", "-shortest", out_path]
    run_cmd(cmd)
    return out_path
