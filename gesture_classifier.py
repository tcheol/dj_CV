# Gesture map
# 
#     open_palm     – all 5 fingers up              → Play / Pause
#     fist          – all fingers down              → Stop
#     thumb_up      – only thumb up, tip above wrist
#     thumb_down    – only thumb down, tip below wrist
#     point         – only index up                 → Select song card
#     peace         – index + middle up             → Toggle loop
#     three_fingers – index + middle + ring up      → Next track
#     pinky         – only pinky up                 → Previous track
#     rock_on       – index + pinky up (horns)      → Crossfade

from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


WRIST = 0

THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP,  INDEX_PIP,  INDEX_DIP,  INDEX_TIP  = 5,  6,  7,  8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9,  10, 11, 12
RING_MCP,   RING_PIP,   RING_DIP,   RING_TIP   = 13, 14, 15, 16
PINKY_MCP,  PINKY_PIP,  PINKY_DIP,  PINKY_TIP  = 17, 18, 19, 20


# A finger is "extended" when its tip is this much *above* (lower y) its PIP.
# Expressed as a fraction of the wrist-to-middle-MCP distance so it scales
# with hand size / camera distance.
EXTENSION_RATIO: float = 0.10

# Thumb: tip must be this much *above* wrist.y (normalised) to count as up.
THUMB_UP_RATIO: float = 0.05

# Thumb is considered active only when it is clearly extended away from the palm.
THUMB_EXTENDED_RATIO: float = 0.08

# Internal helpers

def _lm(hand, idx):
    """Return the (x, y) tuple for a landmark by index."""
    lm = hand.landmark[idx]
    return lm.x, lm.y


def _hand_scale(hand) -> float:
    """
    Reference length = wrist → middle-finger MCP distance.
    Used to normalise thresholds so they work at any camera distance.
    Returns a small positive float; never zero.
    """
    wx, wy   = _lm(hand, WRIST)
    mx, my   = _lm(hand, MIDDLE_MCP)
    dist = ((mx - wx) ** 2 + (my - wy) ** 2) ** 0.5
    return dist if dist > 1e-6 else 1e-6


def _finger_extended(hand, tip_idx: int, pip_idx: int, scale: float) -> bool:
    """
    True when the finger tip is sufficiently *above* (smaller y) its PIP joint.
    MediaPipe y increases downward, so tip.y < pip.y means the finger is up.
    """
    _, tip_y = _lm(hand, tip_idx)
    _, pip_y = _lm(hand, pip_idx)
    return (pip_y - tip_y) > EXTENSION_RATIO * scale


def _thumb_extended(hand, scale: float) -> bool:
    """True when the thumb is clearly extended away from the palm (up OR down)."""
    tx, ty = _lm(hand, THUMB_TIP)
    ipx, ipy = _lm(hand, THUMB_IP)
    cmx, cmy = _lm(hand, THUMB_CMC)

    # Vertical extension: tip above IP (up) OR tip below IP (down)
    vertical = abs(ipy - ty) > (THUMB_UP_RATIO * scale / 2)
    horizontal = abs(tx - cmx) > THUMB_EXTENDED_RATIO * scale
    return vertical or horizontal


def _thumb_up(hand, scale: float) -> bool:
    """
    Thumb is pointing upward when its tip is above the wrist.
    """
    _, tip_y  = _lm(hand, THUMB_TIP)
    _, wrist_y = _lm(hand, WRIST)
    return tip_y < wrist_y


# Public classifier

def classify(hand) -> Optional[str]:
    """
    Classify a MediaPipe ``hand_landmarks`` object into a gesture name.

    Parameters

    hand : mediapipe.framework.formats.landmark_pb2.NormalizedLandmarkList
        A single hand's landmarks as returned by MediaPipe Hands.

    Returns

    str | None
        Gesture name, or ``None`` if no gesture matches.
    """
    scale = _hand_scale(hand)

    # Finger states
    thumb  = _thumb_extended(hand, scale)
    thumb_up = _thumb_up(hand, scale)
    index  = _finger_extended(hand, INDEX_TIP,  INDEX_PIP,  scale)
    middle = _finger_extended(hand, MIDDLE_TIP, MIDDLE_PIP, scale)
    ring   = _finger_extended(hand, RING_TIP,   RING_PIP,   scale)
    pinky  = _finger_extended(hand, PINKY_TIP,  PINKY_PIP,  scale)

    # Rock on (index + pinky) -> horns gesture
    if index and pinky and not middle and not ring:
        return 'rock_on'

    # All fingers down → fist
    if not any([thumb, index, middle, ring, pinky]):
        return 'fist'

    # All 5 up → open palm
    if all([thumb, index, middle, ring, pinky]):
        return 'open_palm'

    # Thumb only
    if thumb and not index and not middle and not ring and not pinky:
        _, tip_y   = _lm(hand, THUMB_TIP)
        _, wrist_y = _lm(hand, WRIST)
        return 'thumb_up' if tip_y < wrist_y else 'thumb_down'

    # Index only → point
    if index and not thumb and not middle and not ring and not pinky:
        return 'point'

    # Index + middle → peace
    if index and middle and not thumb and not ring and not pinky:
        return 'peace'

    # Index + middle + ring → three_fingers
    if index and middle and ring and not thumb and not pinky:
        return 'three_fingers'

    # Pinky only → previous track
    if pinky and not thumb and not index and not middle and not ring:
        return 'pinky'

    return None


# Debouncer

@dataclass
class GestureDebouncer:
    """
    Prevents noisy hand-tracking from spamming events.

    A gesture is *fired* only when it has been seen consistently for
    ``confirm_frames`` consecutive frames.  Once fired it is not fired
    again until a different (or absent) gesture breaks the streak.

    Parameters

    confirm_frames : int
        Consecutive frames required before a gesture fires.
    cooldown_frames : int
        Minimum frames between two firings of the *same* gesture.
        Set to 0 to allow continuous firing (useful for crossfade / volume).

    Example

        debouncer = GestureDebouncer(confirm_frames=6, cooldown_frames=20)

        while True:
            raw    = classify(hand)
            fired  = debouncer.update(raw)
            if fired:
                bus.dispatch(fired)
    """

    confirm_frames:  int = 8
    cooldown_frames: int = 20

    # Internal state (not meant to be touched externally)
    _candidate:       Optional[str] = field(default=None, repr=False, init=False)
    _streak:          int           = field(default=0,    repr=False, init=False)
    _last_fired:      Optional[str] = field(default=None, repr=False, init=False)
    _cooldown_left:   int           = field(default=0,    repr=False, init=False)

    def update(self, raw: Optional[str]) -> Optional[str]:
        """
        Feed the latest raw gesture and return a confirmed event (or None).

        Parameters
        raw : str | None
            Output of ``classify()`` for the current frame.

        Returns

        str | None
            The gesture name if it just fired, else ``None``.
        """
        # Tick cooldown counter down every frame
        if self._cooldown_left > 0:
            self._cooldown_left -= 1

        # Streak tracking
        if raw == self._candidate:
            self._streak += 1
        else:
            self._candidate = raw
            self._streak    = 1

        # Not yet stable enough → no event
        if self._streak < self.confirm_frames:
            return None

        # Gesture confirmed – check cooldown
        gesture = self._candidate
        if gesture is None:
            return None

        if gesture == self._last_fired and self._cooldown_left > 0:
            return None

        # Fire!
        self._last_fired    = gesture
        self._cooldown_left = self.cooldown_frames
        return gesture

    def reset(self) -> None:
        """Hard-reset all state (call when no hand is visible)."""
        self._candidate     = None
        self._streak        = 0
        self._last_fired    = None
        self._cooldown_left = 0


# Quick sanity-check (run directly: python gesture_classifier.py)

if __name__ == '__main__':
    print('gesture_classifier.py loaded OK')
    print('Gestures recognised:', [
        'open_palm', 'fist', 'thumb_up', 'thumb_down',
        'point', 'peace', 'three_fingers', 'pinky', 'rock_on',
    ])
    d = GestureDebouncer(confirm_frames=4, cooldown_frames=10)
    # Simulate 5 frames of "fist"
    for i in range(5):
        result = d.update('fist')
        print(f'  frame {i+1}: update("fist") → {result}')
