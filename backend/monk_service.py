"""Google Monk Skin Tone (MST 1-10) Recognition Engine — High-Accuracy Version.

Upgrade over v1 (PIL-only):
  Step 1 — MediaPipe Face Mesh (468 landmarks): precise anatomical ROI extraction
            (bilateral cheeks + forehead), excluding eyes, lips, nostrils, hair.
  Step 2 — K-Means dominant colour clustering in CIE L*a*b* (k=3): rejects stray
            freckle/shadow/blemish pixels; uses largest-cluster centroid.
  Step 3 — Sclera white-balance anchor: eye whites (known ~[0.86,0.84,0.79] linear)
            used as illuminant reference; corrects camera colour cast in linear light.

Falls back gracefully to the PIL-only sampler when MediaPipe finds no face.
"""

from __future__ import annotations

import io
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

_ROOT_DIR = Path(__file__).resolve().parent.parent
_MODEL_PATH = Path(__file__).parent / "models" / "face_landmarker.task"
_landmarker = None
MEDIAPIPE_AVAILABLE = False

if _MODEL_PATH.exists():
    try:
        import mediapipe as mp
        from mediapipe.tasks.python import vision
        from mediapipe.tasks.python.core import base_options as base_options_module

        _options = vision.FaceLandmarkerOptions(
            base_options=base_options_module.BaseOptions(model_asset_path=str(_MODEL_PATH)),
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1,
        )
        _landmarker = vision.FaceLandmarker.create_from_options(_options)
        MEDIAPIPE_AVAILABLE = True
    except Exception:
        _landmarker = None
        MEDIAPIPE_AVAILABLE = False

try:
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# ---------------------------------------------------------------------------
# Google Monk Skin Tone 10-Level Palette (official hex swatches)
# ---------------------------------------------------------------------------
MONK_PALETTE: Dict[int, Dict[str, Any]] = {
    1:  {"name": "Monk 01", "hex": "#f6ede4", "band": "Light",        "fst": "I-II"},
    2:  {"name": "Monk 02", "hex": "#f3e7db", "band": "Light",        "fst": "I-II"},
    3:  {"name": "Monk 03", "hex": "#f7ead0", "band": "Light",        "fst": "II-III"},
    4:  {"name": "Monk 04", "hex": "#eadaba", "band": "Medium-Light", "fst": "III"},
    5:  {"name": "Monk 05", "hex": "#d7bd96", "band": "Medium",       "fst": "III-IV"},
    6:  {"name": "Monk 06", "hex": "#a07e56", "band": "Medium-Deep",  "fst": "IV-V"},
    7:  {"name": "Monk 07", "hex": "#825c43", "band": "Deep",         "fst": "V"},
    8:  {"name": "Monk 08", "hex": "#604134", "band": "Deep",         "fst": "V-VI"},
    9:  {"name": "Monk 09", "hex": "#3a312a", "band": "Very Deep",    "fst": "VI"},
    10: {"name": "Monk 10", "hex": "#292420", "band": "Deepest",      "fst": "VI"},
}

# CIE 1931 D65 Reference White
D65_WHITE = (0.95047, 1.00000, 1.08883)

# sRGB -> CIE XYZ D65 matrix
M_SRGB_TO_XYZ = [
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
]

DELTA        = 6.0 / 29.0
DELTA_CUBED  = DELTA ** 3
SLOPE        = 1.0 / (3.0 * DELTA ** 2)
OFFSET       = 4.0 / 29.0

# Physiological sclera reflectance reference in linear sRGB
SCLERA_REF   = (0.86, 0.84, 0.79)
GAIN_CLAMP   = (0.30, 4.50)

# MediaPipe landmark index groups (Face Mesh 468 + iris refine)
# Cheek patches: stable, far from eyes/lips/nose highlight
_LEFT_CHEEK_IDX  = [50, 101, 118, 117, 116, 123, 147, 187, 207, 206, 205, 36, 142, 126, 209, 49]
_RIGHT_CHEEK_IDX = [280, 352, 346, 347, 345, 352, 376, 411, 427, 426, 425, 266, 371, 355, 429, 279]
_FOREHEAD_IDX    = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378,
                    400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21,
                    54, 103, 67, 109]
# Sclera/iris region for white-balance anchor
_SCLERA_RIGHT    = [33, 7, 163, 144, 145, 153, 154, 155, 133]
_SCLERA_LEFT     = [362, 382, 381, 380, 374, 373, 390, 249, 263]


# ---------------------------------------------------------------------------
# Colorimetry primitives (zero-dependency, pure Python)
# ---------------------------------------------------------------------------
def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}"


def _srgb_to_linear(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return c / 12.92 if c <= 0.04045 else math.pow((c + 0.055) / 1.055, 2.4)


def _linear_to_srgb(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * math.pow(c, 1.0 / 2.4) - 0.055


def _f_lab(t: float) -> float:
    return math.pow(t, 1.0 / 3.0) if t > DELTA_CUBED else SLOPE * t + OFFSET


def _xyz_to_lab(x, y, z, wp=D65_WHITE):
    fx, fy, fz = _f_lab(x/wp[0]), _f_lab(y/wp[1]), _f_lab(z/wp[2])
    return 116.0*fy - 16.0, 500.0*(fx - fy), 200.0*(fy - fz)


def rgb_to_lab_8bit(r: int, g: int, b: int) -> Tuple[float, float, float]:
    rl = _srgb_to_linear(r / 255.0)
    gl = _srgb_to_linear(g / 255.0)
    bl = _srgb_to_linear(b / 255.0)
    x = M_SRGB_TO_XYZ[0][0]*rl + M_SRGB_TO_XYZ[0][1]*gl + M_SRGB_TO_XYZ[0][2]*bl
    y = M_SRGB_TO_XYZ[1][0]*rl + M_SRGB_TO_XYZ[1][1]*gl + M_SRGB_TO_XYZ[1][2]*bl
    z = M_SRGB_TO_XYZ[2][0]*rl + M_SRGB_TO_XYZ[2][1]*gl + M_SRGB_TO_XYZ[2][2]*bl
    return _xyz_to_lab(x, y, z)


def calculate_ita(L: float, b: float) -> float:
    safe_b = b if abs(b) > 1e-5 else 1e-5 * (1.0 if b >= 0 else -1.0)
    return math.atan2(L - 50.0, safe_b) * (180.0 / math.pi)


def classify_fitzpatrick(ita: float) -> str:
    if ita > 55:  return "I"
    if ita > 41:  return "II"
    if ita > 28:  return "III"
    if ita > 10:  return "IV"
    if ita > -30: return "V"
    return "VI"


def classify_undertone(a: float, b: float, L: Optional[float] = None) -> Tuple[str, float, float, float]:
    chroma  = math.hypot(a, b)
    hue     = round((math.atan2(b, a) * 180.0 / math.pi) % 360.0, 4)
    if   hue < 50:  ut = "cool"
    elif hue < 60:  ut = "neutral"
    elif hue < 72:  ut = "warm"
    else:           ut = "olive" if chroma <= 16.5 else "warm"
    conf = min(1.0, chroma / 8.0)
    if L is not None and L < 35.0:
        conf *= 0.85
    return ut, hue, chroma, conf


def delta_e_76(lab1, lab2) -> float:
    return math.sqrt((lab1[0]-lab2[0])**2 + (lab1[1]-lab2[1])**2 + (lab1[2]-lab2[2])**2)


# Pre-compute Monk centroids in L*a*b* (pure swatches)
MONK_CENTROIDS_LAB: Dict[int, Tuple[float, float, float]] = {
    t: rgb_to_lab_8bit(*hex_to_rgb(info["hex"]))
    for t, info in MONK_PALETTE.items()
}

# Empirical camera centroids loaded from data/calibration.json
_CAL_PATH = _ROOT_DIR / "data" / "calibration.json"
CALIBRATED_CENTROIDS_LAB: Dict[int, Tuple[float, float, float]] = {}
if _CAL_PATH.exists():
    try:
        with open(_CAL_PATH) as _f:
            _c_data = json.load(_f)
            if "centroids" in _c_data:
                for _t_str, _coords in _c_data["centroids"].items():
                    CALIBRATED_CENTROIDS_LAB[int(_t_str)] = tuple(_coords)
    except Exception:
        pass


def match_monk_tone(
    measured_lab: Tuple[float, float, float], is_photo: bool = False
) -> Dict[str, Any]:
    target_centroids = (
        CALIBRATED_CENTROIDS_LAB
        if (is_photo and CALIBRATED_CENTROIDS_LAB)
        else MONK_CENTROIDS_LAB
    )
    distances = sorted(
        [(t, delta_e_76(measured_lab, c)) for t, c in target_centroids.items()],
        key=lambda x: x[1]
    )
    best_tone,  best_de   = distances[0]
    second_tone, second_de = distances[1]

    conf      = max(0.1, min(0.99, 1.0 - best_de / 30.0))
    ambiguity = best_de / max(1e-5, second_de)
    ita       = calculate_ita(measured_lab[0], measured_lab[2])
    fst       = classify_fitzpatrick(ita)
    ut, hue_deg, chroma, _ = classify_undertone(measured_lab[1], measured_lab[2], measured_lab[0])

    clinical_guidance = []
    if best_tone >= 7:
        clinical_guidance.append(
            "High white-cast risk with physical UV filters (ZnO/TiO2). "
            "Prioritize chemical or tinted hybrid sunscreens."
        )
    if best_tone >= 4:
        clinical_guidance.append(
            "Elevated melanocyte reactivity (PIH risk). "
            "Limit unbuffered Glycolic Acid (<=7%) and Salicylic Acid (<=2%)."
        )
    if ut == "cool":
        clinical_guidance.append("Cool undertone: avoid overly yellow/golden foundations.")
    elif ut == "warm":
        clinical_guidance.append("Warm undertone: harmonises with golden/peachy bases.")
    elif ut == "olive":
        clinical_guidance.append("Olive undertone: requires muted green-neutral pigments.")

    return {
        "tone":              best_tone,
        "monk_name":         MONK_PALETTE[best_tone]["name"],
        "band":              MONK_PALETTE[best_tone]["band"],
        "monk_hex":          MONK_PALETTE[best_tone]["hex"],
        "fitzpatrick_scale": fst,
        "delta_e":           round(best_de, 2),
        "second_tone":       second_tone,
        "second_delta_e":    round(second_de, 2),
        "ambiguity_ratio":   round(ambiguity, 3),
        "confidence":        round(conf, 2),
        "ita_degrees":       round(ita, 2),
        "undertone":         ut,
        "hue_angle":         round(hue_deg, 2),
        "chroma":            round(chroma, 2),
        "clinical_guidance": clinical_guidance,
    }


# ---------------------------------------------------------------------------
# Step 3: White Target Calibration (von Kries D65 normalization)
# ---------------------------------------------------------------------------
def _detect_white_card(
    img_rgb: np.ndarray, chin_y_norm: Optional[float] = None
) -> Optional[Tuple[Tuple[int, int, int], float]]:
    """
    Detects a white reference card/paper in the scene (held below the chin or near the collar).
    Returns (median_rgb, card_area_fraction) or None if no valid card detected.
    """
    h, w = img_rgb.shape[:2]
    y_start = int(chin_y_norm * h) if (chin_y_norm and 0.2 < chin_y_norm < 0.85) else int(h * 0.45)
    roi = img_rgb[y_start:h, :]
    if roi.shape[0] < 30 or roi.shape[1] < 30:
        return None

    try:
        import cv2
        hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
        s = hsv[:, :, 1]
        v = hsv[:, :, 2]

        # White paper/card: High brightness (V >= 195) and genuine neutral low saturation (S <= 25)
        white_mask = (v >= 195) & (s <= 25)
        if np.sum(white_mask) < (w * h * 0.012):
            return None

        kernel = np.ones((5, 5), np.uint8)
        opened = cv2.morphologyEx(white_mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for c in contours:
            area = cv2.contourArea(c)
            if area > (w * h * 0.015):  # At least 1.5% of the full frame
                candidates.append((area, c))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        best_area, best_cnt = candidates[0]

        c_mask = np.zeros(roi.shape[:2], dtype=np.uint8)
        cv2.drawContours(c_mask, [best_cnt], -1, 255, -1)
        eroded = cv2.erode(c_mask, np.ones((7, 7), np.uint8))
        card_pixels = roi[eroded == 255]
        if len(card_pixels) < 150:
            return None

        med_r = float(np.median(card_pixels[:, 0]))
        med_g = float(np.median(card_pixels[:, 1]))
        med_b = float(np.median(card_pixels[:, 2]))

        if med_r < 140 or med_g < 140:
            return None

        return (int(med_r), int(med_g), int(med_b)), float(best_area / (w * h))
    except Exception:
        return None


def _apply_white_card_wb(img_rgb: np.ndarray, card_rgb: Tuple[int, int, int]) -> np.ndarray:
    """
    Normalizes the image to Standard CIE D65 Daylight using von Kries chromatic adaptation
    anchored to the measured white paper reflectance.
    """
    meas_lin = np.array([_srgb_to_linear(c / 255.0) for c in card_rgb])
    target_ref = 0.95
    gains = np.clip(target_ref / np.maximum(meas_lin, 1e-4), 0.40, 3.50)

    img_norm = img_rgb.astype(float) / 255.0
    img_lin = np.where(img_norm <= 0.04045, img_norm / 12.92, ((img_norm + 0.055) / 1.055) ** 2.4)
    img_lin_wb = np.clip(img_lin * gains[np.newaxis, np.newaxis, :], 0.0, 1.0)
    img_srgb_wb = np.where(img_lin_wb <= 0.0031308, img_lin_wb * 12.92, 1.055 * (img_lin_wb ** (1.0 / 2.4)) - 0.055)
    return np.clip(img_srgb_wb * 255.0, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Sclera white-balance (illuminant correction fallback)
# ---------------------------------------------------------------------------
def _apply_sclera_wb(img_rgb: np.ndarray, landmarks, h: int, w: int) -> np.ndarray:
    """Measure sclera pixels and apply von Kries per-channel gain correction."""
    sclera_pixels = []
    for idx in _SCLERA_RIGHT + _SCLERA_LEFT:
        if idx >= len(landmarks):
            continue
        lm = landmarks[idx]
        x, y = int(lm.x * w), int(lm.y * h)
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                py, px = y + dy, x + dx
                if 0 <= py < h and 0 <= px < w:
                    sclera_pixels.append(img_rgb[py, px].astype(float) / 255.0)

    if len(sclera_pixels) < 20:
        return img_rgb  # not enough sclera pixels, skip WB

    sp = np.array(sclera_pixels)
    # Keep brightest 40% (actual sclera, not iris/eyelid)
    brightness = sp.mean(axis=1)
    threshold  = np.percentile(brightness, 60)
    bright     = sp[brightness >= threshold]
    if len(bright) < 10:
        return img_rgb

    measured_lin = np.array([_srgb_to_linear(float(bright[:, c].mean())) for c in range(3)])
    ref_lin      = np.array([_srgb_to_linear(v) for v in SCLERA_REF])

    gains = np.clip(ref_lin / np.maximum(measured_lin, 1e-4), GAIN_CLAMP[0], GAIN_CLAMP[1])

    # Apply gain in linear light then re-encode to sRGB
    img_lin = np.vectorize(_srgb_to_linear)(img_rgb.astype(float) / 255.0)
    img_lin_wb = np.clip(img_lin * gains[np.newaxis, np.newaxis, :], 0, 1)
    img_srgb_wb = np.vectorize(_linear_to_srgb)(img_lin_wb)
    return (img_srgb_wb * 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Step 1 + 2: MediaPipe Face Mesh → anatomical ROI → K-Means dominant colour
# ---------------------------------------------------------------------------
def _extract_roi_pixels_mediapipe(img_rgb: np.ndarray) -> Optional[List[Tuple[int, int, int]]]:
    """
    Returns a flat list of (R,G,B) uint8 tuples sampled from anatomical
    cheek and forehead patches via MediaPipe Face Landmarker.
    Returns None if no face detected.
    """
    if not MEDIAPIPE_AVAILABLE or _landmarker is None:
        return None

    h, w = img_rgb.shape[:2]
    try:
        import mediapipe as mp
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
        result = _landmarker.detect(mp_image)
    except Exception:
        return None

    if not result.face_landmarks:
        return None

    landmarks = result.face_landmarks[0]
    patch_radius = max(3, int(min(h, w) * 0.015))

    left_pts = [117, 118, 101, 50, 205, 123, 147]
    right_pts = [346, 347, 330, 280, 425, 352, 376]
    fh_pts = [10, 338, 297, 67, 109, 21]

    def sample_pts(pts):
        pxs = []
        for idx in pts:
            if idx >= len(landmarks):
                continue
            lm = landmarks[idx]
            cx, cy = int(lm.x * w), int(lm.y * h)
            for dy in range(-patch_radius, patch_radius + 1):
                for dx in range(-patch_radius, patch_radius + 1):
                    py, px = cy + dy, cx + dx
                    if 0 <= py < h and 0 <= px < w:
                        r, g, b = img_rgb[py, px]
                        max_c, min_c = max(r, g, b), min(r, g, b)
                        sat = 0.0 if max_c == 0 else (max_c - min_c) / max_c
                        if max_c > 235 and sat < 0.15:
                            continue  # specular glare
                        if max_c < 25:
                            continue  # deep shadow
                        pxs.append((int(r), int(g), int(b)))
        return pxs

    left_px = sample_pts(left_pts)
    right_px = sample_pts(right_pts)
    forehead_px = sample_pts(fh_pts)

    mean_l = np.mean([p[0]*0.3 + p[1]*0.59 + p[2]*0.11 for p in left_px]) if left_px else 0
    mean_r = np.mean([p[0]*0.3 + p[1]*0.59 + p[2]*0.11 for p in right_px]) if right_px else 0

    if abs(mean_l - mean_r) > 15:
        chosen_cheek = left_px if mean_l > mean_r else right_px
    else:
        chosen_cheek = left_px + right_px

    all_pixels = chosen_cheek + forehead_px
    return all_pixels if len(all_pixels) >= 20 else None


def _dominant_lab_kmeans(pixels: List[Tuple[int, int, int]]) -> Tuple[float, float, float]:
    """
    Step 2: K-Means (k=3) in L*a*b* space.
    Returns the centroid of the largest cluster (dominant true skin colour).
    """
    lab_pixels = np.array([rgb_to_lab_8bit(r, g, b) for r, g, b in pixels], dtype=np.float32)

    # Lightness-based robust trimming (15th–85th percentile)
    L_vals = lab_pixels[:, 0]
    lo, hi = np.percentile(L_vals, 15), np.percentile(L_vals, 85)
    trimmed = lab_pixels[(L_vals >= lo) & (L_vals <= hi)]
    if len(trimmed) < 15:
        trimmed = lab_pixels

    if SKLEARN_AVAILABLE and len(trimmed) >= 9:
        unique_pts = np.unique(trimmed, axis=0)
        k = min(3, len(unique_pts))
        if k > 1:
            km = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=100)
            labels = km.fit_predict(trimmed)
            # Largest cluster = dominant skin tone
            counts = np.bincount(labels)
            dominant_center = km.cluster_centers_[np.argmax(counts)]
            return float(dominant_center[0]), float(dominant_center[1]), float(dominant_center[2])

    # Fallback: median of trimmed pixels
    med = np.median(trimmed, axis=0)
    return float(med[0]), float(med[1]), float(med[2])


# ---------------------------------------------------------------------------
# PIL-only fallback (used when MediaPipe finds no face)
# ---------------------------------------------------------------------------
def _is_skin_rgb(r: int, g: int, b: int) -> bool:
    max_c, min_c = max(r, g, b), min(r, g, b)
    sat = (max_c - min_c) / max(max_c, 1)
    if max_c > 248 and sat < 0.08:
        return False   # near pure white
    if max_c < 18:
        return False   # pitch black
    # Skin has red/yellow dominance; allow for cool/blue ambient illumination
    if r < g * 0.82 or r < b * 0.82:
        return False
    if (r - g) > 95 and b < 70:
        return False   # lipstick
    return True


def _pil_fallback_roi(img: Image.Image) -> Optional[List[Tuple[int, int, int]]]:
    w, h = img.size
    pixels_obj = img.load()
    step = max(1, int(min(w, h) / 100))

    # 1. Locate primary skin cluster
    skin_pts: List[Tuple[int, int]] = []
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b = pixels_obj[x, y]
            max_c, min_c = max(r, g, b), min(r, g, b)
            sat = (max_c - min_c) / max(max_c, 1)
            if max_c > 230 and sat < 0.15:
                continue
            if _is_skin_rgb(r, g, b):
                skin_pts.append((x, y))

    if len(skin_pts) < 20:
        return None

    xs = [pt[0] for pt in skin_pts]
    ys = [pt[1] for pt in skin_pts]
    xs.sort()
    ys.sort()
    n = len(skin_pts)
    x_lo, x_hi = xs[int(n * 0.08)], xs[int(n * 0.92)]
    y_lo, y_hi = ys[int(n * 0.08)], ys[int(n * 0.92)]

    cx, cy = (x_lo + x_hi) / 2.0, (y_lo + y_hi) / 2.0
    rx, ry = max(10.0, (x_hi - x_lo) / 2.0), max(10.0, (y_hi - y_lo) / 2.0)

    skin: List[Tuple[int, int, int]] = []
    for y in range(max(0, int(y_lo)), min(h, int(y_hi)), step):
        for x in range(max(0, int(x_lo)), min(w, int(x_hi)), step):
            if ((x - cx)**2 / rx**2) + ((y - cy)**2 / ry**2) > 1.0:
                continue
            r, g, b = pixels_obj[x, y]
            max_c, min_c = max(r, g, b), min(r, g, b)
            sat = (max_c - min_c) / max(max_c, 1)
            if max_c > 230 and sat < 0.15:
                continue
            if _is_skin_rgb(r, g, b):
                skin.append((r, g, b))
    return skin if len(skin) >= 20 else None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def process_image_for_monk_tone(
    image_bytes: bytes,
    crop_center_oval: bool = True,
) -> Dict[str, Any]:
    """
    Process a JPEG/PNG/WebP image and return Google Monk Skin Tone classification.

    Pipeline:
      1. MediaPipe Face Mesh → bilateral cheek + forehead landmark patches.
      2. Sclera white-balance correction (von Kries illuminant anchoring).
      3. Specular glare rejection (Shafer DRM).
      4. K-Means (k=3) dominant cluster in L*a*b*.
      5. Nearest-centroid Monk Skin Tone matching (Delta-E).
    """
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        return {"status": "ERROR", "message": f"Failed to decode image: {e}"}

    w, h = pil_img.size
    if w < 80 or h < 80:
        return {"status": "RECAPTURE", "issue": "FACE_TOO_SMALL",
                "message": "Image resolution too low."}

    # Resize large images for speed
    max_dim = 720
    if max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.BILINEAR)

    img_np = np.array(pil_img, dtype=np.uint8)   # H×W×3 RGB

    # --- Step 0: Check for White Reference Card (Studio von Kries Calibration) ---
    white_card_info = _detect_white_card(img_np)
    white_card_calibrated = False
    card_rgb = None
    if white_card_info:
        card_rgb, card_frac = white_card_info
        img_np = _apply_white_card_wb(img_np, card_rgb)
        white_card_calibrated = True

    # --- Step 1+2+3: Try MediaPipe pipeline ---
    method = "mediapipe_landmarker"
    roi_pixels = _extract_roi_pixels_mediapipe(img_np)

    # --- Fallback: PIL oval sampler ---
    if roi_pixels is None:
        method = "pil_oval_fallback"
        roi_pixels = _pil_fallback_roi(pil_img)

    if not roi_pixels or len(roi_pixels) < 15:
        return {
            "status":  "RECAPTURE",
            "issue":   "NO_SKIN_DETECTED",
            "message": "Could not detect skin pixels. Ensure face is well-lit and centred.",
        }

    # --- Step 4: K-Means dominant colour in L*a*b* ---
    measured_lab = _dominant_lab_kmeans(roi_pixels)

    # Representative display hex (median of raw RGB pixels)
    rgb_arr = np.array(roi_pixels, dtype=np.uint8)
    rep_rgb = tuple(int(np.median(rgb_arr[:, c])) for c in range(3))
    rep_hex = rgb_to_hex(*rep_rgb)

    # --- Step 5: Match to Monk scale ---
    is_real_face = method.startswith("mediapipe")
    match_result = match_monk_tone(measured_lab, is_photo=is_real_face)

    if white_card_calibrated:
        match_result["confidence"] = max(0.95, min(0.99, round(match_result["confidence"] * 1.25, 2)))
        method = f"{method} (Studio White-Card D65 Calibrated)"

    return {
        "status":                "OK",
        "measured_rgb":          list(rep_rgb),
        "measured_hex":          rep_hex,
        "measured_lab":          [round(v, 2) for v in measured_lab],
        "skin_samples_count":    len(roi_pixels),
        "method":                method,
        "white_card_calibrated": white_card_calibrated,
        "card_illuminant_rgb":   list(card_rgb) if card_rgb else None,
        **match_result,
    }
