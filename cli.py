#!/usr/bin/env python3
"""Command line interface for the English to Tamil video dubber."""

import argparse
import sys

from dubbing import DubbingError
from dubbing.pipeline import load_config, run_pipeline


def build_parser():
    parser = argparse.ArgumentParser(
        description="Dub an English video into Tamil.",
        epilog="Only dub content you own or have permission to adapt.",
    )
    parser.add_argument("input", help="video URL (YouTube etc.) or path to a local video file")
    parser.add_argument("-o", "--output", help="output .mp4 path (default: output/<name>_ta.mp4)")
    parser.add_argument("-c", "--config", help="path to a config YAML (default: config.yaml)")
    parser.add_argument("--voice", help="edge-tts voice, e.g. ta-IN-ValluvarNeural")
    parser.add_argument("--model", help="Whisper model size: tiny, base, small, medium, large-v3")
    parser.add_argument("--engine", choices=["google", "nllb"], help="translation engine")
    parser.add_argument(
        "--keep-original", action="store_true",
        help="mix the original audio quietly under the Tamil voice",
    )
    parser.add_argument(
        "--subtitles", action="store_true", help="embed Tamil subtitles as a soft track",
    )
    parser.add_argument(
        "--keep-temp", action="store_true", help="keep intermediate files in the workspace",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    overrides = {
        "transcription": {"model_size": args.model},
        "translation": {"engine": args.engine},
        "tts": {"voice": args.voice},
        "merge": {
            "keep_original_audio": True if args.keep_original else None,
            "subtitles": True if args.subtitles else None,
        },
        "keep_temp": True if args.keep_temp else None,
    }

    def show(fraction, message):
        print(f"[{int(fraction * 100):3d}%] {message}", flush=True)

    try:
        config = load_config(args.config, overrides)
        result = run_pipeline(args.input, output=args.output, config=config, progress=show)
    except DubbingError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130

    print(f"\nDubbed video: {result['video']}")
    print(f"Subtitles:    {result['subtitles']}")
    print(f"Transcript:   {result['segments_file']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
