"""
cv_engine/utils.py
------------------
Shared geometric helpers used by every exercise evaluator.
"""
import math
import mediapipe as mp



def calculate_angle(a, b, c) -> float:
    """
    Calculate the interior angle at point B formed by the vectors B->A and B->C.
    Points are (x, y) tuples in normalised [0,1] image space.
    Returns degrees in [0, 180].
    """
    ax, ay = a[0] - b[0], a[1] - b[1]
    cx, cy = c[0] - b[0], c[1] - b[1]
    dot   = ax * cx + ay * cy
    mag_a = math.hypot(ax, ay)
    mag_c = math.hypot(cx, cy)
    if mag_a * mag_c == 0:
        return 0.0
    cos_a = max(-1.0, min(1.0, dot / (mag_a * mag_c)))
    return math.degrees(math.acos(cos_a))


def check_visibility(landmarks, indices: list, threshold: float = 0.6) -> bool:
    """Return True only if ALL specified landmark indices meet the visibility threshold."""
    return all(landmarks[i].visibility >= threshold for i in indices)


def lm_xy(landmarks, index: int):
    """Return (x, y) tuple for a landmark index."""
    lm = landmarks[index]
    return lm.x, lm.y


def lm_y(landmarks, index: int) -> float:
    return landmarks[index].y


def lm_x(landmarks, index: int) -> float:
    return landmarks[index].x
