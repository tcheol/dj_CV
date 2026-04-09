import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONGS_DIR = os.path.join(BASE_DIR, 'songs')
SONGS_JSON = os.path.join(BASE_DIR, 'songs.json')

# ── Window ──────────────────────────────────────────────
WINDOW_NAME = 'DJ Controller  |  Q=quit  I=import'

# ── Song panel (top-left overlay) ───────────────────────
PANEL_X, PANEL_Y   = 10, 10
PANEL_WIDTH        = 245
CARD_HEIGHT        = 66
CARD_PADDING       = 5
IMPORT_BTN_HEIGHT  = 38
MAX_VISIBLE_SONGS  = 5
# Total panel height is computed dynamically in ui_renderer

# ── Colors (BGR for OpenCV) ──────────────────────────────
COL_PANEL_BG        = (22, 22, 22)
COL_CARD_DEFAULT    = (48, 48, 52)
COL_CARD_HOVER      = (55, 95, 55)
COL_CARD_PLAYING    = (28, 135, 28)
COL_CARD_QUEUED     = (65, 65, 115)
COL_TEXT_PRIMARY    = (228, 228, 228)
COL_TEXT_SECONDARY  = (150, 150, 150)
COL_ACCENT          = (0, 210, 90)
COL_IMPORT_BTN      = (38, 75, 135)
COL_GESTURE_BADGE   = (0, 130, 210)
COL_STATUS_BAR      = (18, 18, 18)

# ── Gesture tuning ───────────────────────────────────────
# A gesture must be held for this many frames before it fires
GESTURE_HOLD_FRAMES    = 10
# After firing, ignore new gestures for this many frames
GESTURE_COOLDOWN_FRAMES = 22
# Volume gestures repeat every N frames while held
VOLUME_REPEAT_INTERVAL  = 4
# Normalized 0-1 distance between thumb tip & index tip to count as pinch
PINCH_THRESHOLD         = 0.07

# ── Audio ────────────────────────────────────────────────
DEFAULT_VOLUME  = 0.70
CROSSFADE_MS    = 3000   # duration of crossfade in milliseconds
SAMPLE_RATE     = 44100

# ── WebSocket server ─────────────────────────────────────
WS_PORT      = 8765
JPEG_QUALITY = 60        # 0-100; lower = smaller frames over WS
