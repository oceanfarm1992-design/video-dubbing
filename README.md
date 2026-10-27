# video-dubbing

Dub English videos into Tamil. Give it a YouTube link or a local video file and it returns the same video with a Tamil voice track, plus an optional Tamil subtitle file.

## How it works

```
video URL / file
      |
      v
 downloader.py   yt-dlp download, ffmpeg audio extraction
      |
      v
 transcriber.py  faster-whisper: English speech -> timed segments
      |
      v
 translator.py   English -> Tamil (Google via deep-translator, or offline NLLB)
      |
      v
 tts_engine.py   edge-tts: Tamil neural voices, one clip per segment
      |
      v
 audio_sync.py   speed clips up to fit each slot, place them on one timeline
      |
      v
 merger.py       mux with the original video, optional soft subtitles
```

`dubbing/pipeline.py` runs these steps in order. `cli.py` and `app.py` are two front ends on top of it.

## Requirements

- Python 3.10 or newer
- [ffmpeg](https://ffmpeg.org/) (including `ffprobe`) on your PATH
- An internet connection for downloads, the default translator and the Tamil voices

## Quick start

```bash
git clone https://github.com/oceanfarm1992-design/video-dubbing.git
cd video-dubbing
bash setup.sh
source .venv/bin/activate
```

On Windows, run the same commands in WSL or Git Bash, or create a virtual environment by hand and run `pip install -r requirements.txt`.

## Usage

### Command line

```bash
# Local file
python cli.py my_video.mp4

# YouTube link, male voice, bigger Whisper model, keep quiet original audio
python cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
    --voice ta-IN-ValluvarNeural --model medium --keep-original

# Embed Tamil subtitles and choose the output path
python cli.py my_video.mp4 --subtitles -o dubbed/my_video_tamil.mp4
```

Results are written to `output/` by default:

- `<name>_ta.mp4` the dubbed video
- `<name>_ta.srt` Tamil subtitles
- `<name>_ta.segments.json` English text, Tamil text and timings for each segment, useful for proofreading

Run `python cli.py --help` for every option.

### Web interface

```bash
python app.py
```

Open the printed local address, paste a URL or upload a file, pick a voice and press **Dub video**.

## Configuration

All defaults live in [`config.yaml`](config.yaml). The important ones:

| Setting | Purpose |
| --- | --- |
| `transcription.model_size` | Whisper size. Larger is more accurate and slower. |
| `translation.engine` | `google` (online, no key needed) or `nllb` (offline, needs the optional packages in `requirements.txt`). |
| `tts.voice` | Any Tamil edge-tts voice, for example `ta-IN-PallaviNeural` (female) or `ta-IN-ValluvarNeural` (male). |
| `sync.max_speedup` | How much Tamil speech may be sped up to fit the original timing. |
| `merge.keep_original_audio` | Mix the original audio quietly under the Tamil voice. |
| `merge.subtitles` | Embed the Tamil subtitles as a soft track in the mp4. |

List all available Tamil voices with `edge-tts --list-voices | grep ta-`.

## Project layout

```
video-dubbing/
├── README.md
├── requirements.txt
├── .gitignore
├── config.yaml
├── setup.sh
├── cli.py
├── app.py
└── dubbing/
    ├── __init__.py
    ├── downloader.py
    ├── transcriber.py
    ├── translator.py
    ├── tts_engine.py
    ├── audio_sync.py
    ├── merger.py
    └── pipeline.py
```

## Tips and limitations

- Tamil is usually longer than English, so the dub is sped up to fit. If speech sounds rushed, raise `sync.max_overflow`, use a shorter source, or edit the segments and re-run.
- Machine translation can miss names, idioms and technical terms. Check the `.segments.json` file before publishing.
- A single voice is used for the whole video. Multiple speakers are not separated.
- The dub replaces the original audio unless you enable `merge.keep_original_audio`. Music and sound effects are only kept in that mode, at low volume.
- Downloaded videos stay under the rules of their original platform and copyright owner. Only dub content you own or have permission to adapt.
