"""Step 4: synthesize Tamil speech for every translated segment with edge-tts."""

import asyncio
from pathlib import Path

from . import DubbingError


async def _synthesize_all(jobs, voice, rate, pitch, concurrency):
    import edge_tts

    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def one(text, out_path):
        async with semaphore:
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(str(out_path))

    await asyncio.gather(*(one(text, path) for text, path in jobs))


def synthesize_segments(
    segments,
    out_dir,
    voice="ta-IN-PallaviNeural",
    rate="+0%",
    pitch="+0Hz",
    concurrency=4,
):
    """Generate one mp3 per segment. Returns a list aligned with `segments`.

    Segments with no translated text get None.
    """
    try:
        import edge_tts  # noqa: F401
    except ImportError as exc:
        raise DubbingError(
            "edge-tts is not installed. Run: pip install -r requirements.txt"
        ) from exc

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    clips = [None] * len(segments)
    jobs = []
    for index, seg in enumerate(segments):
        if seg.translation.strip():
            path = out_dir / f"seg_{index:04d}.mp3"
            clips[index] = path
            jobs.append((seg.translation, path))

    if not jobs:
        raise DubbingError("There is no translated text to synthesize.")

    try:
        asyncio.run(_synthesize_all(jobs, voice, rate, pitch, concurrency))
    except Exception as exc:
        raise DubbingError(f"Text-to-speech failed (voice {voice}): {exc}") from exc

    return clips
