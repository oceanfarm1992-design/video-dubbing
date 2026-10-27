"""Step 2: speech to text with faster-whisper, keeping timestamps for each segment."""

from dataclasses import asdict, dataclass

from . import DubbingError


@dataclass
class Segment:
    start: float
    end: float
    text: str
    translation: str = ""

    def to_dict(self):
        return asdict(self)


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

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    raw_segments, _info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=vad_filter,
        beam_size=5,
    )

    segments = []
    for item in raw_segments:
        text = item.text.strip()
        if text:
            segments.append(Segment(start=float(item.start), end=float(item.end), text=text))

    if not segments:
        raise DubbingError("No speech was detected in the audio.")
    return segments
