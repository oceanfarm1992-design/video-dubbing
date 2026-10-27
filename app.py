#!/usr/bin/env python3
"""Gradio web interface for the English to Tamil video dubber."""

import json

import gradio as gr

from dubbing import DubbingError
from dubbing.pipeline import load_config, run_pipeline

VOICES = [
    "ta-IN-PallaviNeural",
    "ta-IN-ValluvarNeural",
    "ta-LK-SaranyaNeural",
    "ta-LK-KumarNeural",
    "ta-MY-KaniNeural",
    "ta-MY-SuryaNeural",
    "ta-SG-VenbaNeural",
    "ta-SG-AnbuNeural",
]
MODELS = ["tiny", "base", "small", "medium", "large-v3"]


def dub(url, upload, voice, model_size, keep_original, subtitles, progress=gr.Progress()):
    source = upload or (url or "").strip()
    if not source:
        raise gr.Error("Paste a video URL or upload a video file.")

    overrides = {
        "transcription": {"model_size": model_size},
        "tts": {"voice": voice},
        "merge": {"keep_original_audio": keep_original, "subtitles": subtitles},
    }
    try:
        config = load_config(overrides=overrides)
        result = run_pipeline(source, config=config, progress=lambda f, m: progress(f, desc=m))
    except DubbingError as exc:
        raise gr.Error(str(exc)) from exc

    transcript = json.dumps(
        [seg.to_dict() for seg in result["segments"]], ensure_ascii=False, indent=2
    )
    return str(result["video"]), str(result["subtitles"]), transcript


def build_ui():
    with gr.Blocks(title="English to Tamil Video Dubbing") as demo:
        gr.Markdown(
            "# English to Tamil video dubbing\n"
            "Transcribe, translate and re-voice a video in Tamil. "
            "Only dub content you own or have permission to adapt."
        )
        with gr.Row():
            with gr.Column():
                url = gr.Textbox(label="Video URL", placeholder="https://www.youtube.com/watch?v=...")
                upload = gr.Video(label="...or upload a video", sources=["upload"])
                voice = gr.Dropdown(VOICES, value=VOICES[0], label="Tamil voice")
                model_size = gr.Dropdown(MODELS, value="small", label="Whisper model")
                keep_original = gr.Checkbox(label="Keep original audio quietly in the background")
                subtitles = gr.Checkbox(label="Embed Tamil subtitles")
                run = gr.Button("Dub video", variant="primary")
            with gr.Column():
                video_out = gr.Video(label="Dubbed video")
                srt_out = gr.File(label="Tamil subtitles (.srt)")
                transcript_out = gr.Code(label="Segments (English and Tamil)", language="json")

        run.click(
            dub,
            inputs=[url, upload, voice, model_size, keep_original, subtitles],
            outputs=[video_out, srt_out, transcript_out],
        )
    return demo


if __name__ == "__main__":
    build_ui().queue().launch()
