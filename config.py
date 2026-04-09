
# ─────────────────────────────────────────────
#  config.py  –  Global constants
# ─────────────────────────────────────────────
 
# ── Window ────────────────────────────────────
WINDOW_NAME = "Gesture DJ Controller"
 
# ── Camera ────────────────────────────────────
# Index of the camera device to open.
# 0 = default / built-in webcam.
# Change to 1, 2, … to use an external camera.
CAMERA_INDEX = 0
 
# Preferred capture resolution (width × height).
# The camera will fall back gracefully if the
# hardware doesn't support this resolution.
CAMERA_WIDTH  = 1280
CAMERA_HEIGHT = 720
 
# Target frame-rate (frames per second).
# Most webcams cap at 30; higher values are
# accepted silently but may not be honoured.
CAMERA_FPS = 30
 
# Mirror the frame horizontally so it acts like
# a natural reflection for the user.
CAMERA_MIRROR = True
 
# ── Display ───────────────────────────────────
# Resize the display window on startup.
# Set to None to use the raw capture resolution.
DISPLAY_WIDTH  = 1280
DISPLAY_HEIGHT = 720
