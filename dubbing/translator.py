"""Step 3: translate each segment's text into Tamil."""

import time

from . import DubbingError

_NLLB_CODES = {
    "en": "eng_Latn",
    "ta": "tam_Taml",
    "hi": "hin_Deva",
    "te": "tel_Telu",
    "ml": "mal_Mlym",
    "kn": "kan_Knda",
}


_GOOGLE_API = "https://translate.googleapis.com/translate_a/single"


def _google_api_translate(text, source, target):
    """Translate with Google's public gtx endpoint.

    deep-translator scrapes translate.google.com/m, which Google often answers
    with a CAPTCHA page (HTTP 429) even for a handful of requests.
    """
    import requests

    response = requests.get(
        _GOOGLE_API,
        params={"client": "gtx", "sl": source, "tl": target, "dt": "t", "q": text},
        timeout=20,
    )
    response.raise_for_status()
    return "".join(part[0] for part in response.json()[0] if part and part[0])


def _deep_translator_translate(text, source, target):
    try:
        from deep_translator import GoogleTranslator
    except ImportError as exc:
        raise DubbingError(
            "deep-translator is not installed. Run: pip install -r requirements.txt"
        ) from exc
    return GoogleTranslator(source=source, target=target).translate(text)


def _translate_google(segments, source, target, retries=3):
    for seg in segments:
        last_error = None
        for attempt in range(retries):
            try:
                try:
                    text = _google_api_translate(seg.text, source, target)
                except Exception as exc:
                    last_error = exc
                    text = _deep_translator_translate(seg.text, source, target)
                seg.translation = (text or "").strip()
                break
            except Exception as exc:
                last_error = exc
                time.sleep(1.5 * (attempt + 1))
        else:
            raise DubbingError(f"Translation failed for {seg.text!r}: {last_error}")


def _translate_nllb(segments, source, target, model_name):
    try:
        from transformers import pipeline
    except ImportError as exc:
        raise DubbingError(
            "The nllb engine needs extra packages: pip install transformers sentencepiece torch"
        ) from exc

    if source not in _NLLB_CODES or target not in _NLLB_CODES:
        raise DubbingError(f"Unsupported language pair for nllb: {source} -> {target}")

    translate = pipeline(
        "translation",
        model=model_name,
        src_lang=_NLLB_CODES[source],
        tgt_lang=_NLLB_CODES[target],
        max_length=400,
    )
    outputs = translate([seg.text for seg in segments], batch_size=8)
    for seg, out in zip(segments, outputs):
        seg.translation = out["translation_text"].strip()


def translate_segments(
    segments,
    engine="google",
    source="en",
    target="ta",
    nllb_model="facebook/nllb-200-distilled-600M",
):
    """Fill in `translation` on every segment (in place) and return the list."""
    if engine == "google":
        _translate_google(segments, source, target)
    elif engine == "nllb":
        _translate_nllb(segments, source, target, nllb_model)
    else:
        raise DubbingError(f"Unknown translation engine: {engine!r} (use 'google' or 'nllb')")
    return segments
