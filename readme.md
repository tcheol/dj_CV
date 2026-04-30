# DJ_CV — Gesture-Controlled DJ App

Control music playback with your hands. DJ_CV uses your webcam and computer vision to recognize hand gestures in real time, mapping them to DJ actions like play, pause, volume, crossfade, and track selection.

---

## Features

- **10 hand gestures** mapped to DJ controls (play, pause, stop, volume up/down, next/previous track, loop, crossfade, and more)
- **Two-deck audio engine** with smooth crossfading between tracks
- **Live hand tracking overlay** rendered on the webcam feed
- **Scrollable song library** with drag-to-reorder, metadata display, and waveform visualization
- **Fullscreen mode** for live DJ setups
- **Persistent song library** saved to `songs.json`

---

## Requirements

- Python 3.7+
- A webcam

### Install dependencies

Install all required packages:

```bash
pip install opencv-python mediapipe pygame pillow numpy
```

Install recommended packages (metadata reading — falls back to filename without it):

```bash
pip install mutagen
```

Install optional packages for MP3, FLAC, AAC, and M4A support:

```bash
pip install pydub
```

`pydub` also requires **ffmpeg** installed on your system and available on your PATH:
- Windows: download from https://ffmpeg.org/download.html, extract it, and add the `bin` folder to your system PATH
- You can verify it works by running `ffmpeg -version` in a terminal

Without ffmpeg, only WAV and OGG files will load.

### Download the MediaPipe hand model

Download `hand_landmarker.task` and place it in the project root (same folder as `main.py`):

```
https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

---

## Running

```bash
python main.py
```

---

## Gesture Controls

| Gesture | Hand Shape | Action |
|---|---|---|
| Open palm | All 5 fingers extended | Play / Pause |
| Fist | All fingers curled | Stop |
| Thumbs up | Thumb up, above wrist | Volume up |
| Thumbs down | Thumb down, below wrist | Volume down |
| Point | Index finger only | Hover / select song |
| Peace | Index + middle extended | Toggle loop |
| Three fingers | Index + middle + ring extended | Next track |
| Pinky | Pinky only | Previous track |
| Rock on (horns) | Index + pinky only | Crossfade to selected song |

Gesture recognition uses **debouncing** — hold a gesture for ~8 consistent frames before it fires, preventing accidental triggers from camera noise.

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `I` | Open import dialog |
| `F` or `F11` | Toggle fullscreen |
| `Escape` | Exit fullscreen |
| `Q` | Quit |

---

## Audio Support

| Format | Requires |
|---|---|
| WAV, OGG | Nothing extra |
| MP3, FLAC, AAC, M4A | pydub + ffmpeg |

---

## Project Structure

```
dj_CV/
├── main.py               # Entry point
├── app_window.py         # Main GUI window (camera feed + song panel)
├── song_panel.py         # Track list sidebar
├── import_dialog.py      # File import modal
├── hand_tracker.py       # MediaPipe hand landmark detection
├── gesture_classifier.py # Finger-pose → gesture classification
├── dj_engine.py          # Two-deck audio mixer (pygame)
├── audio.py              # Extended audio engine with pydub support
├── event_bus.py          # Gesture → DJ action dispatcher
├── song_library.py       # Song collection management
├── config.py             # Global settings (camera, display, audio)
├── songs.json            # Persisted song library
└── hand_landmarker.task  # MediaPipe model (download separately)
```

---

## Configuration

Edit `config.py` to adjust:

- **Camera**: device index, resolution (default 1280×720), FPS, mirroring
- **Display**: window size (default 1194×528)
- **Audio**: sample rate (44100 Hz), default volume (0.8), crossfade duration (3000 ms)
