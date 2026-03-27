# ─────────────────────────────────────────────
#  camera.py  –  Webcam abstraction
# ─────────────────────────────────────────────

import sys
import cv2

from config import (
    CAMERA_INDEX,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    CAMERA_FPS,
    CAMERA_MIRROR,
    DISPLAY_WIDTH,
    DISPLAY_HEIGHT,
)


class CameraManager:
    """
    Wraps cv2.VideoCapture with:
      • Clean open / read / release interface
      • Graceful resolution fallback
      • Optional horizontal mirroring
      • FPS and display-size configuration
    """

    def __init__(self):
        self._cap    = None
        self._mirror = CAMERA_MIRROR
        self._open()

    # ── Lifecycle ─────────────────────────────

    def _open(self) -> None:
        """Open the camera and apply settings. Exits the process on failure."""
        self._cap = cv2.VideoCapture(CAMERA_INDEX)

        if not self._cap.isOpened():
            print(
                f"[ERROR] Cannot open camera at index {CAMERA_INDEX}. "
                "Check that your camera is connected and not in use."
            )
            sys.exit(1)

        # Request preferred settings; the driver may ignore them silently.
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS,          CAMERA_FPS)

        # Log the actual values the driver accepted.
        actual_w   = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h   = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self._cap.get(cv2.CAP_PROP_FPS)

        if actual_w != CAMERA_WIDTH or actual_h != CAMERA_HEIGHT:
            print(
                f"[WARN] Requested {CAMERA_WIDTH}×{CAMERA_HEIGHT} but camera "
                f"opened at {actual_w}×{actual_h}. Continuing anyway."
            )
        else:
            print(f"[INFO] Camera opened at {actual_w}×{actual_h} @ {actual_fps:.0f} fps")

    def release(self) -> None:
        """Release the camera resource. Safe to call multiple times."""
        if self._cap and self._cap.isOpened():
            self._cap.release()
            print("[INFO] Camera released.")

    # ── Frame access ──────────────────────────

    def read(self):
        """
        Capture one frame.

        Returns
        -------
        frame : np.ndarray | None
            The (optionally mirrored) BGR frame, or None if the read failed.
        """
        ret, frame = self._cap.read()

        if not ret or frame is None:
            print("[WARN] Failed to read frame from camera.")
            return None

        if self._mirror:
            frame = cv2.flip(frame, 1)

        return frame

    # ── Properties ────────────────────────────

    @property
    def width(self) -> int:
        """Actual capture width reported by the driver."""
        return int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def height(self) -> int:
        """Actual capture height reported by the driver."""
        return int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    @property
    def fps(self) -> float:
        """Actual FPS reported by the driver."""
        return self._cap.get(cv2.CAP_PROP_FPS)

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    # ── Context manager support ───────────────

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.release()
