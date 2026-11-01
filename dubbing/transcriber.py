"""Step 2: speech to text with faster-whisper, keeping timestamps for each segment."""

import logging
import wave
from dataclasses import asdict, dataclass

from . import DubbingError

log = logging.getLogger(__name__)


@dataclass
class Segment:
    start: float
    end: float
    text: str
    translation: str = ""

    def to_dict(self):
        return asdict(self)


def _load_wav(audio_path):
    """Read the 16 kHz mono PCM wav from extract_audio as float32 samples.

    Passing samples instead of a path keeps faster-whisper from decoding with
    PyAV, whose newer releases break faster-whisper's decode_audio call.
    """
    import numpy as np

    with wave.open(str(audio_path), "rb") as wav:
        if wav.getsampwidth() != 2 or wav.getnchannels() != 1 or wav.getframerate() != 16000:
            raise DubbingError(f"Expected 16 kHz mono 16-bit wav: {audio_path}")
        frames = wav.readframes(wav.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe(
    audio_path,
    model_size="small",
    device="auto",
    compute_type="auto",
    language="en",
    vad_filter=True,
):
    """Transcribe audio and return a list of timed Segments."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise DubbingError(
            "faster-whisper is not installed. Run: pip install -r requirements.txt"
        ) from exc

    samples = _load_wav(audio_path)

    def run(dev, ctype):
        model = WhisperModel(model_size, device=dev, compute_type=ctype)
        raw_segments, _info = model.transcribe(
            samples, language=language, vad_filter=vad_filter, beam_size=5
        )
        # Segments are generated lazily, so GPU errors only surface while iterating.
        return [
            Segment(start=float(item.start), end=float(item.end), text=item.text.strip())
            for item in raw_segments
            if item.text.strip()
        ]

    try:
        segments = run(device, compute_type)
    except RuntimeError as exc:
        # "auto" picks CUDA whenever an NVIDIA GPU is present, even if the CUDA
        # libraries (cuBLAS, cuDNN) are missing. Fall back to the CPU then.
        if device == "cpu" or not any(k in str(exc).lower() for k in ("cuda", "cublas", "cudnn")):
            raise
        log.warning("GPU transcription failed (%s); falling back to CPU.", exc)
        segments = run("cpu", "int8")

    if not segments:
        raise DubbingError("No speech was detected in the audio.")
    return segments
