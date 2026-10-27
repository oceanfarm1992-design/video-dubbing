"""Ties every step together: download -> transcribe -> translate -> speak -> sync -> merge."""

import json
import shutil
import time
from pathlib import Path

import yaml

from . import DubbingError, media_duration
from .audio_sync import build_dub_track
from .downloader import download_video, extract_audio
from .merger import merge, write_srt
from .transcriber import transcribe
from .translator import translate_segments
from .tts_engine import synthesize_segments

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.yaml"


def _deep_update(base, new):
    for key, value in (new or {}).items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        elif value is not None:
            base[key] = value
    return base


def load_config(path=None, overrides=None):
    """Load config.yaml (or another file) and apply a nested dict of overrides."""
    path = Path(path) if path else DEFAULT_CONFIG
    if not path.is_file():
        raise DubbingError(f"Config file not found: {path}")
    with open(path, encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    return _deep_update(config, overrides)


def run_pipeline(source, output=None, config=None, progress=None):
    """Dub `source` (URL or file path) into Tamil.

    `progress` is an optional callable taking (fraction, message).
    Returns a dict with the output video, subtitle file, segments file and segment list.
    """
    cfg = config or load_config()
    report = progress or (lambda fraction, message: None)

    job_dir = Path(cfg.get("workspace", "workspace")) / time.strftime("job_%Y%m%d_%H%M%S")
    job_dir.mkdir(parents=True, exist_ok=True)

    try:
        report(0.02, "Getting the video")
        video = download_video(source, job_dir / "download", cfg["download"]["format"])
        total_duration = media_duration(video)

        report(0.10, "Extracting audio")
        audio = extract_audio(video, job_dir / "audio.wav")

        report(0.15, "Transcribing English speech")
        t = cfg["transcription"]
        segments = transcribe(
            audio,
            model_size=t["model_size"],
            device=t["device"],
            compute_type=t["compute_type"],
            language=t["language"],
            vad_filter=t["vad_filter"],
        )

        report(0.45, f"Translating {len(segments)} segments to Tamil")
        tr = cfg["translation"]
        translate_segments(
            segments,
            engine=tr["engine"],
            source=tr["source"],
            target=tr["target"],
            nllb_model=tr["nllb_model"],
        )

        report(0.60, "Generating Tamil speech")
        tts = cfg["tts"]
        clips = synthesize_segments(
            segments,
            job_dir / "tts",
            voice=tts["voice"],
            rate=tts["rate"],
            pitch=tts["pitch"],
            concurrency=tts.get("concurrency", 4),
        )

        report(0.78, "Fitting speech to the original timing")
        sync = cfg["sync"]
        dub_wav = build_dub_track(
            segments,
            clips,
            total_duration,
            job_dir / "dub.wav",
            job_dir / "fit",
            sample_rate=sync["sample_rate"],
            max_speedup=sync["max_speedup"],
            max_overflow=sync.get("max_overflow", 1.4),
        )

        report(0.90, "Merging audio and video")
        out_video = Path(output) if output else (
            Path(cfg.get("output_dir", "output")) / f"{video.stem}_ta.mp4"
        )
        out_video.parent.mkdir(parents=True, exist_ok=True)
        srt_path = write_srt(segments, out_video.with_suffix(".srt"))
        m = cfg["merge"]
        merge(
            video,
            dub_wav,
            out_video,
            keep_original_audio=m["keep_original_audio"],
            original_volume=m["original_volume"],
            dubbed_volume=m["dubbed_volume"],
            srt_path=srt_path if m.get("subtitles") else None,
        )

        segments_path = out_video.with_suffix(".segments.json")
        segments_path.write_text(
            json.dumps([seg.to_dict() for seg in segments], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        report(1.0, "Done")
        return {
            "video": out_video,
            "subtitles": srt_path,
            "segments_file": segments_path,
            "segments": segments,
        }
    finally:
        if not cfg.get("keep_temp", False):
            shutil.rmtree(job_dir, ignore_errors=True)
