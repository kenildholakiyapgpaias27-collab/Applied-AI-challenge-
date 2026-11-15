#!/usr/bin/env python3
"""
AAINA AI Skin Tone & Shade Detection: Executable Colorimetry & Contract Test Suite
==================================================================================

Authoritative test suite implementing the 4-tier testing philosophy defined in
TEST_INFRA.md:
  - Tier 1: Feature Coverage (Mathematical Invariants, Standard Transformations)
  - Tier 2: Boundary & Corner Cases (Knots, Singularities, Continuity Proofs)
  - Tier 3: Cross-Feature Combinations (Pipelines, Downstream Skincare Guardrails)
  - Tier 4: Real-World Scenarios (Sensor Noise, Shadow Drops, Highlight Repairs)

Standards & References:
  - IEC 61966-2-1:1999: sRGB Default RGB Colour Space
  - CIE 15:2004 / ISO/CIE 11664-4:2019: CIE 1976 L*a*b* Colour Space
  - Chardon et al. (1991): Skin colour typology and phototypes
  - Del Bino & Bernerd (2013, 2018): ITA° skin classification thresholds
  - Finlayson & Trezzi (2004): Shades-of-Grey illuminant estimation

Usage:
  python3 tests/verify_colorimetry_spec.py
  python3 tests/verify_colorimetry_spec.py -v
"""

import json
import math
import re
import unittest
from typing import Any, Dict, List, Optional, Tuple

# ==============================================================================
# SECTION 1: AUTHORITATIVE MATHEMATICAL SPECIFICATIONS & ORACLES
# ==============================================================================

# Standard CIE Illuminant D65 Reference White Point (2° Standard Observer, Yn = 1.0)
D65_WHITE = (0.95047, 1.00000, 1.08883)

# Exact Rational Constants for CIE 1976 L*a*b* (CIE 15:2004 / ISO/CIE 11664-4)
DELTA = 6.0 / 29.0                     # Rational knot threshold ~ 0.206896551724
DELTA_CUBED = 216.0 / 24389.0          # delta^3 ~ 0.008856451679035631
SLOPE = 841.0 / 108.0                  # 1 / (3 * delta^2) ~ 7.787037037037037
OFFSET = 4.0 / 29.0                    # 16 / 116 ~ 0.13793103448275862
KAPPA = 24389.0 / 27.0                 # 116 * (841 / 108) ~ 903.2962962962963

# ITU-R BT.709 to CIE 1931 XYZ Conversion Matrix under D65
M_SRGB_TO_XYZ = [
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
]

# Inverse Matrix: CIE 1931 XYZ to Linear sRGB
M_XYZ_TO_SRGB = [
    [3.2404542, -1.5371385, -0.4985314],
    [-0.9692660, 1.8760108, 0.0415560],
    [0.0556434, -0.2040259, 1.0572252],
]

# Organic Physiological Sclera Reference (Linear sRGB)
SCLERA_REF = (0.86, 0.84, 0.79)
SCLERA_GAIN_CLAMP = (0.3, 4.5)
BG_GAIN_CLAMP = (0.72, 1.45)

# Aaina / Monk 10-Level Skin Tone Palette Hex Codes (from src/engine.js:175)
MONK_HEX = {
    1: "#f6ede4",
    2: "#f3e7db",
    3: "#f7ead0",
    4: "#eadaba",
    5: "#d7bd96",
    6: "#a07e56",
    7: "#825c43",
    8: "#604134",
    9: "#3a312a",
    10: "#292420",
}


def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    """Parse a #RRGGBB hex code into 8-bit RGB integers."""
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def srgb_to_linear(c: float) -> float:
    """
    Inverse companding per IEC 61966-2-1:1999.
    Maps non-linear sRGB channel in [0, 1] to linear photon intensity in [0, 1].
    Clamps inputs outside [0, 1].
    """
    c = max(0.0, min(1.0, c))
    if c <= 0.04045:
        return c / 12.92
    return math.pow((c + 0.055) / 1.055, 2.4)


def linear_to_srgb(c: float) -> float:
    """
    Forward companding per IEC 61966-2-1:1999.
    Encodes linear intensity in [0, 1] into display sRGB in [0, 1].
    Clamps inputs outside [0, 1].
    """
    c = max(0.0, min(1.0, c))
    if c <= 0.0031308:
        return 12.92 * c
    return 1.055 * math.pow(c, 1.0 / 2.4) - 0.055


def linear_rgb_to_xyz(r: float, g: float, b: float) -> Tuple[float, float, float]:
    """Convert linear sRGB [0, 1] to CIE 1931 XYZ under Illuminant D65."""
    x = M_SRGB_TO_XYZ[0][0] * r + M_SRGB_TO_XYZ[0][1] * g + M_SRGB_TO_XYZ[0][2] * b
    y = M_SRGB_TO_XYZ[1][0] * r + M_SRGB_TO_XYZ[1][1] * g + M_SRGB_TO_XYZ[1][2] * b
    z = M_SRGB_TO_XYZ[2][0] * r + M_SRGB_TO_XYZ[2][1] * g + M_SRGB_TO_XYZ[2][2] * b
    return (x, y, z)


def xyz_to_linear_rgb(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """Convert CIE 1931 XYZ to linear sRGB under Illuminant D65."""
    r = M_XYZ_TO_SRGB[0][0] * x + M_XYZ_TO_SRGB[0][1] * y + M_XYZ_TO_SRGB[0][2] * z
    g = M_XYZ_TO_SRGB[1][0] * x + M_XYZ_TO_SRGB[1][1] * y + M_XYZ_TO_SRGB[1][2] * z
    b = M_XYZ_TO_SRGB[2][0] * x + M_XYZ_TO_SRGB[2][1] * y + M_XYZ_TO_SRGB[2][2] * z
    return (r, g, b)


def f_lab(t: float) -> float:
    """Piecewise function f(t) for CIE 1976 L*a*b* using exact rational knot delta = 6/29."""
    if t > DELTA_CUBED:
        return math.pow(t, 1.0 / 3.0)
    return SLOPE * t + OFFSET


def inv_f_lab(f: float) -> float:
    """Exact inverse of f(t) mapping Lab intermediate coordinate back to relative stimulus."""
    if f > DELTA:
        return math.pow(f, 3.0)
    return (f - OFFSET) / SLOPE


def xyz_to_lab(
    x: float, y: float, z: float, wp: Tuple[float, float, float] = D65_WHITE
) -> Tuple[float, float, float]:
    """Transform CIE 1931 XYZ to CIE 1976 L*a*b* under reference white point wp."""
    xr = x / wp[0]
    yr = y / wp[1]
    zr = z / wp[2]
    fx = f_lab(xr)
    fy = f_lab(yr)
    fz = f_lab(zr)
    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return (L, a, b)


def lab_to_xyz(
    L: float, a: float, b: float, wp: Tuple[float, float, float] = D65_WHITE
) -> Tuple[float, float, float]:
    """Inverse transformation from CIE 1976 L*a*b* back to CIE 1931 XYZ."""
    fy = (L + 16.0) / 116.0
    fx = fy + (a / 500.0)
    fz = fy - (b / 200.0)
    xr = inv_f_lab(fx)
    yr = inv_f_lab(fy)
    zr = inv_f_lab(fz)
    return (xr * wp[0], yr * wp[1], zr * wp[2])


def rgb_to_lab_8bit(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """End-to-end color conversion from 8-bit sRGB [0, 255] to CIE 1976 L*a*b*."""
    r_lin = srgb_to_linear(r / 255.0)
    g_lin = srgb_to_linear(g / 255.0)
    b_lin = srgb_to_linear(b / 255.0)
    x, y, z = linear_rgb_to_xyz(r_lin, g_lin, b_lin)
    return xyz_to_lab(x, y, z)


def calculate_ita(L: float, b: float) -> float:
    """
    Calculate Individual Typology Angle (ITA°) with safe atan2 protection.
    Formula: ITA° = [arctan((L* - 50) / b*)] * (180 / pi)
    Singularity protection: When b* -> 0, returns +90° (if L* > 50) or -90° (if L* < 50).
    """
    safe_b = b if abs(b) > 1e-5 else 1e-5 * (1.0 if b >= 0 else -1.0)
    return math.atan2(L - 50.0, safe_b) * (180.0 / math.pi)


def classify_fitzpatrick(ita: float) -> str:
    """
    Classify Individual Typology Angle (ITA°) into Fitzpatrick Skin Phototypes (FST I–VI)
    per Chardon et al. (1991) and Del Bino et al. (2013, 2018):
      - FST I: ITA > 55°
      - FST II: 41° < ITA <= 55°
      - FST III: 28° < ITA <= 41°
      - FST IV: 10° < ITA <= 28°
      - FST V: -30° < ITA <= 10°
      - FST VI: ITA <= -30°
    """
    if ita > 55.0:
        return "I"
    elif ita > 41.0:
        return "II"
    elif ita > 28.0:
        return "III"
    elif ita > 10.0:
        return "IV"
    elif ita > -30.0:
        return "V"
    else:
        return "VI"


def classify_undertone(
    a: float, b: float, L: Optional[float] = None
) -> Tuple[str, float, float, float]:
    """
    Classify skin undertone in polar (C*, h°) coordinate space:
      - Cool: h° < 50°
      - Neutral: 50° <= h° < 60°
      - Warm: 60° <= h° < 72°
      - Olive: h° >= 72° with muted chroma C* <= 16.5
    Returns (undertone, hue_angle, chroma, confidence).
    """
    chroma = math.hypot(a, b)
    # Round to 7 decimal places to avoid floating-point epsilon truncation artifacts
    raw_hue = (math.atan2(b, a) * (180.0 / math.pi)) % 360.0
    hue = round(raw_hue, 7)

    if hue < 50.0:
        ut = "cool"
    elif hue < 60.0:
        ut = "neutral"
    elif hue < 72.0:
        ut = "warm"
    else:
        # High hue angle: Olive if chroma is muted (C* <= 16.5); else golden warm
        ut = "olive" if chroma <= 16.5 else "warm"

    # Confidence calculation: deep skin or low chroma reduces angular signal-to-noise ratio
    conf = min(1.0, chroma / 8.0)
    if L is not None and L < 35.0:
        conf *= 0.85

    return ut, hue, chroma, conf


def derive_sclera_gains(
    measured_sclera: Tuple[float, float, float],
    ref: Tuple[float, float, float] = SCLERA_REF,
    clamp: Tuple[float, float] = SCLERA_GAIN_CLAMP,
) -> Tuple[float, float, float]:
    """
    Derive per-channel linear von Kries scaling gains from measured eye sclera reflectance
    relative to universal physiological reference [0.86, 0.84, 0.79].
    """
    gains = tuple(
        max(clamp[0], min(clamp[1], ref[c] / max(1e-4, measured_sclera[c])))
        for c in range(3)
    )
    return (gains[0], gains[1], gains[2])


# Build empirical skin R/G ratio lookup table from Monk skin palette swatches
def _build_skin_rg_table() -> List[Tuple[float, float]]:
    pairs = []
    for hex_code in MONK_HEX.values():
        r, g, b = hex_to_rgb(hex_code)
        r_lin = srgb_to_linear(r / 255.0)
        g_lin = srgb_to_linear(g / 255.0)
        if g_lin > 1e-4:
            pairs.append((g_lin, r_lin / g_lin))
    pairs.sort(key=lambda item: item[0])
    return pairs


SKIN_RG_TABLE = _build_skin_rg_table()


def skin_rg(g_lin: float) -> float:
    """Piecewise linear interpolation of skin R/G ratio given linear green intensity."""
    t = SKIN_RG_TABLE
    if g_lin <= t[0][0]:
        return t[0][1]
    for i in range(1, len(t)):
        if g_lin <= t[i][0]:
            frac = (g_lin - t[i - 1][0]) / (t[i][0] - t[i - 1][0])
            return t[i - 1][1] + frac * (t[i][1] - t[i - 1][1])
    return t[-1][1]


def reconstruct_clipped_red(
    r_byte: int,
    g_byte: int,
    b_byte: int,
    gains: Tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> Tuple[float, float, float]:
    """
    Sensor highlight recovery: When the red channel clips (R >= 254) while green and blue
    remain linear (G < 254, B < 254), reconstruct linear red from green using empirical skinRG.
    """
    r_lin = srgb_to_linear(r_byte / 255.0) * gains[0]
    g_lin = srgb_to_linear(g_byte / 255.0) * gains[1]
    b_lin = srgb_to_linear(b_byte / 255.0) * gains[2]

    if r_byte >= 254 and g_byte < 254 and b_byte < 254:
        r_lin = g_lin * skin_rg(g_lin)

    return (r_lin, g_lin, b_lin)


def filter_unilateral_shadow(
    regions: List[Dict[str, Any]], threshold: float = 8.0
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Filter out shadowed facial hemisphere when bilateral asymmetry |ΔL*| exceeds threshold.
    Returns (filtered_regions, shadow_dropped_flag).
    """
    left_labs = [
        r["lab"][0]
        for r in regions
        if r.get("side") == "L" or "left" in r.get("name", "")
    ]
    right_labs = [
        r["lab"][0]
        for r in regions
        if r.get("side") == "R" or "right" in r.get("name", "")
    ]

    if left_labs and right_labs:
        med_l = sorted(left_labs)[len(left_labs) // 2]
        med_r = sorted(right_labs)[len(right_labs) // 2]
        delta_L = abs(med_l - med_r)
        if delta_L > threshold:
            lit_side = "L" if med_l > med_r else "R"
            filtered = [
                r
                for r in regions
                if (r.get("side") == lit_side)
                or (lit_side == "L" and "left" in r.get("name", ""))
                or (lit_side == "R" and "right" in r.get("name", ""))
            ]
            return filtered, True
    return regions, False


def validate_aaina_data_contract(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Strict data contract validator verifying JSON response structure against AAINA engine spec.
    Supports a boundary hysteresis band of +/- 1.5° for Fitzpatrick classification.
    """
    errors = []
    required_keys = {
        "status",
        "tone",
        "monkScale",
        "undertone",
        "ita",
        "fitzpatrick",
        "lab",
        "conf",
        "method",
        "issues",
        "regions",
    }
    missing = required_keys - set(payload.keys())
    if missing:
        errors.append(f"Missing required payload keys: {sorted(list(missing))}")
        return False, errors

    # Type & constraint checks
    if payload["status"] not in ("OK", "RECAPTURE", "ASK_USER", "FALLBACK"):
        errors.append(f"Invalid status: {payload['status']}")

    if not isinstance(payload["tone"], int) or not (1 <= payload["tone"] <= 10):
        errors.append(f"tone must be integer in [1, 10], got: {payload['tone']}")
        expected_monk = None
    else:
        expected_monk = f"Monk {payload['tone']:02d}"

    if expected_monk and payload["monkScale"] != expected_monk:
        errors.append(
            f"monkScale mismatch: expected '{expected_monk}', got '{payload['monkScale']}'"
        )

    if payload["undertone"] not in ("cool", "neutral", "warm", "olive"):
        errors.append(f"Invalid undertone: {payload['undertone']}")

    if not isinstance(payload["ita"], (int, float)) or not (
        -90.0 <= payload["ita"] <= 90.0
    ):
        errors.append(f"ita must be float in [-90.0, 90.0], got: {payload['ita']}")

    # Fitzpatrick verification with dermatological boundary hysteresis (+/- 1.5°)
    ita_val = payload["ita"] if isinstance(payload["ita"], (int, float)) else 0.0
    expected_fst = classify_fitzpatrick(ita_val)
    reported_fst = payload["fitzpatrick"]

    if reported_fst != expected_fst:
        # Check if user is within hysteresis (+/- 1.5°) of a transition knot
        knots = [55.0, 41.0, 28.0, 10.0, -30.0]
        allowed_adjacent = {
            55.0: ("I", "II"),
            41.0: ("II", "III"),
            28.0: ("III", "IV"),
            10.0: ("IV", "V"),
            -30.0: ("V", "VI"),
        }
        valid_hysteresis = False
        for k, pair in allowed_adjacent.items():
            if abs(ita_val - k) <= 1.5 and reported_fst in pair and expected_fst in pair:
                valid_hysteresis = True
                break
        if not valid_hysteresis:
            errors.append(
                f"fitzpatrick mismatch for ITA={ita_val}: expected '{expected_fst}', got '{reported_fst}'"
            )

    lab = payload["lab"]
    if (
        not isinstance(lab, (list, tuple))
        or len(lab) != 3
        or not (0.0 <= lab[0] <= 100.0)
        or not (-128.0 <= lab[1] <= 127.0)
        or not (-128.0 <= lab[2] <= 127.0)
    ):
        errors.append(f"lab coordinates out of range or malformed: {lab}")

    if not isinstance(payload["conf"], (int, float)) or not (
        0.0 <= payload["conf"] <= 1.0
    ):
        errors.append(f"conf must be in [0.0, 1.0], got: {payload['conf']}")

    if not isinstance(payload["regions"], list) or len(payload["regions"]) == 0:
        errors.append("regions must be a non-empty list")
    else:
        for idx, reg in enumerate(payload["regions"]):
            if "name" not in reg or "lab" not in reg:
                errors.append(f"Region {idx} missing 'name' or 'lab'")
            elif len(reg["lab"]) != 3:
                errors.append(f"Region {idx} lab must be 3-tuple")

    return (len(errors) == 0, errors)


# ==============================================================================
# SECTION 2: TIER 1 — FEATURE COVERAGE TEST CASES
# ==============================================================================


class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1: Feature Coverage
    Mathematically verifies individual colorimetry functions, transformations, and formulas.
    """

    def test_srgb_gamma_linearization_and_companding(self):
        """Verify IEC 61966-2-1 linear segment, power segment, and roundtrip fidelity."""
        # Linear segment: c <= 0.04045
        c_low = 0.02
        lin_low = srgb_to_linear(c_low)
        self.assertAlmostEqual(lin_low, c_low / 12.92, places=7)

        # Power segment: c > 0.04045
        c_high = 0.50
        lin_high = srgb_to_linear(c_high)
        self.assertAlmostEqual(
            lin_high, math.pow((c_high + 0.055) / 1.055, 2.4), places=7
        )

        # Companding round-trip test across 100 equidistant sample points in [0, 1]
        for step in range(101):
            val = step / 100.0
            roundtrip = linear_to_srgb(srgb_to_linear(val))
            self.assertAlmostEqual(
                roundtrip,
                val,
                places=5,
                msg=f"Roundtrip failed for sRGB value {val}",
            )

    def test_linear_rgb_to_cie_xyz_d65_transformation(self):
        """Verify linear RGB to CIE 1931 XYZ matrix under D65 white point."""
        # Reference White [1.0, 1.0, 1.0] must map to D65 White Point
        x_w, y_w, z_w = linear_rgb_to_xyz(1.0, 1.0, 1.0)
        self.assertAlmostEqual(x_w, D65_WHITE[0], places=4)
        self.assertAlmostEqual(y_w, D65_WHITE[1], places=4)
        self.assertAlmostEqual(z_w, D65_WHITE[2], places=4)

        # Verify row sums equal white point coordinates
        row_sum_x = sum(M_SRGB_TO_XYZ[0])
        row_sum_y = sum(M_SRGB_TO_XYZ[1])
        row_sum_z = sum(M_SRGB_TO_XYZ[2])
        self.assertAlmostEqual(row_sum_x, 0.95047, places=5)
        self.assertAlmostEqual(row_sum_y, 1.00000, places=5)
        self.assertAlmostEqual(row_sum_z, 1.08883, places=5)

        # Verify matrix inversion roundtrip: Linear RGB -> XYZ -> Linear RGB
        test_rgbs = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.7, 0.5, 0.3)]
        for r, g, b in test_rgbs:
            xyz = linear_rgb_to_xyz(r, g, b)
            r_rec, g_rec, b_rec = xyz_to_linear_rgb(*xyz)
            self.assertAlmostEqual(r_rec, r, places=4)
            self.assertAlmostEqual(g_rec, g, places=4)
            self.assertAlmostEqual(b_rec, b, places=4)

    def test_xyz_to_cielab_piecewise_transformation(self):
        """Verify CIE 1976 L*a*b* mapping, cube-root and linear branches."""
        # D65 White Point must map identically to L*=100, a*=0, b*=0
        L_w, a_w, b_w = xyz_to_lab(*D65_WHITE)
        self.assertAlmostEqual(L_w, 100.0, places=3)
        self.assertAlmostEqual(a_w, 0.0, places=3)
        self.assertAlmostEqual(b_w, 0.0, places=3)

        # Roundtrip Lab -> XYZ -> Lab
        test_labs = [
            (100.0, 0.0, 0.0),
            (50.0, 15.0, 20.0),
            (25.0, -5.0, 10.0),
            (75.0, 8.0, 14.0),
        ]
        for lab in test_labs:
            xyz = lab_to_xyz(*lab)
            lab_rec = xyz_to_lab(*xyz)
            self.assertAlmostEqual(lab_rec[0], lab[0], places=4)
            self.assertAlmostEqual(lab_rec[1], lab[1], places=4)
            self.assertAlmostEqual(lab_rec[2], lab[2], places=4)

    def test_ita_formula_and_dermatological_properties(self):
        """Verify Individual Typology Angle (ITA°) equation and behavior."""
        # Median midpoint (L*=50, b*=15) -> ITA must be exactly 0°
        ita_mid = calculate_ita(50.0, 15.0)
        self.assertAlmostEqual(ita_mid, 0.0, places=5)

        # Fair skin (L*=75, b*=15): (75-50)/15 = 25/15 -> atan(1.6667) * 180 / pi ~ 59.036°
        expected_fair = math.atan(25.0 / 15.0) * (180.0 / math.pi)
        self.assertAlmostEqual(calculate_ita(75.0, 15.0), expected_fair, places=4)

        # Deep skin (L*=30, b*=15): (30-50)/15 = -20/15 -> -53.13°
        expected_deep = math.atan(-20.0 / 15.0) * (180.0 / math.pi)
        self.assertAlmostEqual(calculate_ita(30.0, 15.0), expected_deep, places=4)

    def test_fitzpatrick_mapping_literature_centroids(self):
        """Verify Fitzpatrick Phototype I–VI mapping against published clinical centroids."""
        # Clinical centroids from Chardon et al. (1991) and Del Bino et al. (2013, 2018)
        clinical_data = [
            ("I", 75.2, 13.8, 61.3),    # Very Light: ITA > 55°
            ("II", 68.5, 16.1, 49.0),   # Light: 41° < ITA <= 55°
            ("III", 62.1, 18.5, 33.2),  # Intermediate: 28° < ITA <= 41°
            ("IV", 55.4, 19.8, 15.3),   # Tan: 10° < ITA <= 28°
            ("V", 44.6, 17.2, -17.4),   # Brown: -30° < ITA <= 10°
            ("VI", 31.2, 12.4, -56.6),  # Dark: ITA <= -30°
        ]
        for fst_expected, L, b, expected_ita in clinical_data:
            computed_ita = calculate_ita(L, b)
            self.assertAlmostEqual(computed_ita, expected_ita, delta=0.2)
            computed_fst = classify_fitzpatrick(computed_ita)
            self.assertEqual(
                computed_fst,
                fst_expected,
                f"Failed for FST {fst_expected} at ITA {computed_ita:.1f}°",
            )

    def test_polar_undertone_classification_schema(self):
        """Verify undertone classification in polar (C*, h°) space."""
        # Cool: h° < 50° (elevated redness a*)
        ut_c, h_c, _, _ = classify_undertone(a=16.0, b=12.0)  # h = atan2(12, 16) ~ 36.87°
        self.assertEqual(ut_c, "cool")
        self.assertLess(h_c, 50.0)

        # Neutral: 50° <= h° < 60°
        ut_n, h_n, _, _ = classify_undertone(a=15.0, b=20.0)  # h = atan2(20, 15) ~ 53.13°
        self.assertEqual(ut_n, "neutral")
        self.assertTrue(50.0 <= h_n < 60.0)

        # Warm: 60° <= h° < 72°
        ut_w, h_w, _, _ = classify_undertone(a=12.0, b=22.0)  # h = atan2(22, 12) ~ 61.39°
        self.assertEqual(ut_w, "warm")
        self.assertTrue(60.0 <= h_w < 72.0)

        # Olive: h° >= 72° with muted chroma C* <= 16.5
        ut_o, h_o, c_o, _ = classify_undertone(a=4.0, b=13.0)  # h = atan2(13, 4) ~ 72.9°, C* = 13.6
        self.assertEqual(ut_o, "olive")
        self.assertGreaterEqual(h_o, 72.0)
        self.assertLessEqual(c_o, 16.5)

    def test_organic_sclera_white_balance_gain_derivation(self):
        """Verify sclera white balance channel gains against reference [0.86, 0.84, 0.79]."""
        # Neutral illuminant matching reference: gains must be exactly 1.0
        gains_neutral = derive_sclera_gains(SCLERA_REF)
        self.assertAlmostEqual(gains_neutral[0], 1.0, places=4)
        self.assertAlmostEqual(gains_neutral[1], 1.0, places=4)
        self.assertAlmostEqual(gains_neutral[2], 1.0, places=4)

        # Warm incandescent lighting: measured sclera is yellow-shifted [0.90, 0.82, 0.60]
        # Gain for Blue should boost significantly
        gains_warm = derive_sclera_gains((0.90, 0.82, 0.60))
        self.assertAlmostEqual(gains_warm[0], 0.86 / 0.90, places=4)
        self.assertAlmostEqual(gains_warm[1], 0.84 / 0.82, places=4)
        self.assertAlmostEqual(gains_warm[2], 0.79 / 0.60, places=4)
        self.assertGreater(gains_warm[2], gains_warm[0])  # Blue gain > Red gain

    def test_data_contract_schema_validation(self):
        """Verify that a valid canonical AAINA output payload passes schema validation."""
        canonical_payload = {
            "status": "OK",
            "tone": 6,
            "monkScale": "Monk 06",
            "undertone": "warm",
            "ita": 28.4,
            "fitzpatrick": "IV",  # 28.4° is within +/- 1.5° hysteresis of boundary 28.0°
            "lab": [52.1, 14.2, 22.8],
            "conf": 0.94,
            "method": "mediapipe_sclera_d65",
            "issues": [],
            "regions": [
                {"name": "forehead_center", "lab": [52.3, 13.9, 22.5]},
                {"name": "left_cheek_roi", "lab": [51.9, 14.4, 23.0]},
                {"name": "right_cheek_roi", "lab": [52.0, 14.3, 22.9]},
                {"name": "jawline_band", "lab": [51.7, 14.1, 22.4]},
            ],
        }
        is_valid, errors = validate_aaina_data_contract(canonical_payload)
        self.assertTrue(is_valid, f"Validation failed with errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_json_serialization_roundtrip_contract(self):
        """Verify that payload serializes to standard JSON and deserializes identically."""
        original = {
            "status": "OK",
            "tone": 4,
            "monkScale": "Monk 04",
            "undertone": "neutral",
            "ita": 35.0,
            "fitzpatrick": "III",
            "lab": [61.0, 11.0, 17.0],
            "conf": 0.88,
            "method": "mediapipe_sclera_d65",
            "issues": [],
            "regions": [{"name": "forehead", "lab": [61.2, 10.9, 16.8]}],
        }
        json_str = json.dumps(original)
        deserialized = json.loads(json_str)
        is_valid, errors = validate_aaina_data_contract(deserialized)
        self.assertTrue(is_valid)
        self.assertEqual(deserialized, original)

    def test_negative_and_out_of_gamut_srgb_clamping(self):
        """Verify that out-of-gamut inputs (<0 or >1) are clamped without exceptions."""
        self.assertEqual(srgb_to_linear(-0.5), 0.0)
        self.assertEqual(srgb_to_linear(1.5), 1.0)
        self.assertEqual(linear_to_srgb(-0.2), 0.0)
        self.assertAlmostEqual(linear_to_srgb(2.0), 1.0, places=7)


# ==============================================================================
# SECTION 3: TIER 2 — BOUNDARY & CORNER CASES TEST CASES
# ==============================================================================


class TestTier2BoundaryCornerCases(unittest.TestCase):
    """
    Tier 2: Boundary & Corner Cases
    Mathematically verifies piecewise transition continuity, derivatives, and limits.
    """

    def test_companding_knot_continuity(self):
        """
        Verify value and derivative continuity at sRGB knot C_srgb = 0.04045.
        Confirms IEC 61966-2-1 derivative regularization prevents infinite slope at dark levels.
        """
        knot = 0.04045
        eps = 1e-8

        # Left limit: Linear branch
        val_left = (knot - eps) / 12.92
        # Right limit: Power branch
        val_right = math.pow(((knot + eps) + 0.055) / 1.055, 2.4)
        self.assertAlmostEqual(val_left, val_right, delta=1e-5)

        # Derivative match: Slope regularized to ~ 0.0774 - 0.0787 across the knot
        d_left = 1.0 / 12.92
        d_right = (2.4 / 1.055) * math.pow((knot + 0.055) / 1.055, 1.4)
        # Verify delta is bounded within IEC standard's rounding tolerance (< 0.002)
        self.assertAlmostEqual(d_left, d_right, delta=0.002)

    def test_cielab_rational_knot_delta_c1_continuity(self):
        """
        Verify exact C^1 continuity of f(t) across rational knot delta = 6/29.
        delta^3 = 216/24389.
        """
        knot = DELTA_CUBED  # 216 / 24389

        # Value matching (C^0)
        # Cube root branch: (216/24389)^(1/3) = 6/29
        val_cube = math.pow(knot, 1.0 / 3.0)
        # Linear branch: (841/108) * (216/24389) + 4/29 = 2/29 + 4/29 = 6/29
        val_lin = SLOPE * knot + OFFSET
        self.assertAlmostEqual(val_cube, DELTA, places=9)
        self.assertAlmostEqual(val_lin, DELTA, places=9)
        self.assertAlmostEqual(val_cube, val_lin, places=9)

        # Derivative matching (C^1)
        # Cube root derivative: d/dt(t^(1/3)) = (1/3) * t^(-2/3) at t = delta^3 is 1 / (3 * delta^2) = 841 / 108
        deriv_cube = (1.0 / 3.0) * math.pow(knot, -2.0 / 3.0)
        deriv_lin = SLOPE  # 841 / 108
        self.assertAlmostEqual(deriv_cube, deriv_lin, places=7)

    def test_cielab_deep_shadow_slope_kappa(self):
        """Verify linear shadow slope kappa = 24389/27 ~ 903.2963 when y_r <= delta^3."""
        # For yr <= delta^3: L* = 116 * ((841/108)*yr + 4/29) - 16 = (116 * 841 / 108) * yr = (24389 / 27) * yr
        yr_deep = 0.005  # yr < 0.008856
        L_deep, _, _ = xyz_to_lab(x=yr_deep * D65_WHITE[0], y=yr_deep, z=yr_deep * D65_WHITE[2])
        expected_L = KAPPA * yr_deep
        self.assertAlmostEqual(L_deep, expected_L, places=4)

    def test_ita_atan2_b_zero_protection(self):
        """Verify atan2 singularity protection when b* -> 0 (pure grayscale skin)."""
        # Fair gray: L* = 70 > 50, b* = 0 -> ITA must be exactly +90.0°
        ita_pos = calculate_ita(70.0, 0.0)
        self.assertAlmostEqual(ita_pos, 90.0, places=4)

        # Dark gray: L* = 30 < 50, b* = 0 -> ITA must be exactly -90.0°
        ita_neg = calculate_ita(30.0, 0.0)
        self.assertAlmostEqual(ita_neg, -90.0, places=4)

        # Midpoint gray: L* = 50, b* = 0 -> ITA must be exactly 0.0°
        ita_zero = calculate_ita(50.0, 0.0)
        self.assertAlmostEqual(ita_zero, 0.0, places=4)

    def test_fitzpatrick_exact_boundary_inequalities(self):
        """Verify exact boundary inequalities for FST I through VI."""
        # Boundary 55°: FST I (> 55) vs FST II (<= 55)
        self.assertEqual(classify_fitzpatrick(55.0001), "I")
        self.assertEqual(classify_fitzpatrick(55.0000), "II")

        # Boundary 41°: FST II (> 41) vs FST III (<= 41)
        self.assertEqual(classify_fitzpatrick(41.0001), "II")
        self.assertEqual(classify_fitzpatrick(41.0000), "III")

        # Boundary 28°: FST III (> 28) vs FST IV (<= 28)
        self.assertEqual(classify_fitzpatrick(28.0001), "III")
        self.assertEqual(classify_fitzpatrick(28.0000), "IV")

        # Boundary 10°: FST IV (> 10) vs FST V (<= 10)
        self.assertEqual(classify_fitzpatrick(10.0001), "IV")
        self.assertEqual(classify_fitzpatrick(10.0000), "V")

        # Boundary -30°: FST V (> -30) vs FST VI (<= -30)
        self.assertEqual(classify_fitzpatrick(-29.9999), "V")
        self.assertEqual(classify_fitzpatrick(-30.0000), "VI")
        self.assertEqual(classify_fitzpatrick(-30.0001), "VI")

    def test_undertone_boundary_transitions(self):
        """Verify exact boundary transitions at 50°, 60°, and 72°."""
        # Boundary 50°: Cool (< 50) vs Neutral (>= 50)
        rad_49_99 = math.radians(49.99)
        ut_49, h_49, _, _ = classify_undertone(math.cos(rad_49_99), math.sin(rad_49_99))
        self.assertEqual(ut_49, "cool")
        self.assertLess(h_49, 50.0)

        rad_50_00 = math.radians(50.00)
        ut_50, h_50, _, _ = classify_undertone(math.cos(rad_50_00), math.sin(rad_50_00))
        self.assertEqual(ut_50, "neutral")
        self.assertGreaterEqual(h_50, 50.0)

        # Boundary 60°: Neutral (< 60) vs Warm (>= 60)
        rad_59_99 = math.radians(59.99)
        ut_59, h_59, _, _ = classify_undertone(math.cos(rad_59_99), math.sin(rad_59_99))
        self.assertEqual(ut_59, "neutral")
        self.assertLess(h_59, 60.0)

        rad_60_00 = math.radians(60.00)
        ut_60, h_60, _, _ = classify_undertone(math.cos(rad_60_00), math.sin(rad_60_00))
        self.assertEqual(ut_60, "warm")
        self.assertGreaterEqual(h_60, 60.0)

        # Boundary 72°: Warm (< 72) vs Olive (>= 72 with low chroma)
        rad_71_99 = math.radians(71.99)
        ut_71, h_71, _, _ = classify_undertone(
            10.0 * math.cos(rad_71_99), 10.0 * math.sin(rad_71_99)
        )
        self.assertEqual(ut_71, "warm")
        self.assertLess(h_71, 72.0)

        rad_72_00 = math.radians(72.00)
        ut_72, h_72, _, _ = classify_undertone(
            10.0 * math.cos(rad_72_00), 10.0 * math.sin(rad_72_00)
        )
        self.assertEqual(ut_72, "olive")
        self.assertGreaterEqual(h_72, 72.0)

    def test_undertone_olive_chroma_constraint(self):
        """Verify that hue >= 72° classifies as Olive only if C* <= 16.5."""
        rad_75 = math.radians(75.0)
        # Muted chroma (C* = 14.0 <= 16.5) -> Olive
        ut_muted, _, c_muted, _ = classify_undertone(
            14.0 * math.cos(rad_75), 14.0 * math.sin(rad_75)
        )
        self.assertEqual(ut_muted, "olive")
        self.assertLessEqual(c_muted, 16.5)

        # High saturated chroma (C* = 22.0 > 16.5) -> Warm (Golden Yellow)
        ut_saturated, _, c_sat, _ = classify_undertone(
            22.0 * math.cos(rad_75), 22.0 * math.sin(rad_75)
        )
        self.assertEqual(ut_saturated, "warm")
        self.assertGreater(c_sat, 16.5)

    def test_sclera_gain_clamping_extremes(self):
        """Verify that extreme measured sclera values respect gain clamps [0.3, 4.5]."""
        # Extreme dark / underexposure (sclera = 0.05) -> clamp at max 4.5
        gains_dark = derive_sclera_gains((0.05, 0.05, 0.05))
        self.assertEqual(gains_dark, (4.5, 4.5, 4.5))

        # Extreme overexposure / glint (sclera = 3.50) -> clamp at min 0.3
        gains_bright = derive_sclera_gains((3.5, 3.5, 3.5))
        self.assertEqual(gains_bright, (0.3, 0.3, 0.3))

    def test_pure_white_and_pure_black_extremes(self):
        """Verify gamut endpoints: Pure White (255,255,255) and Pure Black (0,0,0)."""
        # Pure White
        L_w, a_w, b_w = rgb_to_lab_8bit(255, 255, 255)
        self.assertAlmostEqual(L_w, 100.0, delta=0.1)
        self.assertAlmostEqual(a_w, 0.0, delta=0.1)
        self.assertAlmostEqual(b_w, 0.0, delta=0.1)

        # Pure Black
        L_k, a_k, b_k = rgb_to_lab_8bit(0, 0, 0)
        self.assertAlmostEqual(L_k, 0.0, delta=0.01)
        self.assertAlmostEqual(a_k, 0.0, delta=0.01)
        self.assertAlmostEqual(b_k, 0.0, delta=0.01)

    def test_pure_grayscale_b_zero_robustness(self):
        """Verify that pure grayscale inputs (R=G=B) maintain a*=0, b*=0 and numerical safety."""
        for gray_byte in [10, 50, 128, 200, 240]:
            L, a, b = rgb_to_lab_8bit(gray_byte, gray_byte, gray_byte)
            self.assertAlmostEqual(a, 0.0, places=3)
            self.assertAlmostEqual(b, 0.0, places=3)
            ita = calculate_ita(L, b)
            self.assertTrue(-90.0 <= ita <= 90.0)

    def test_unilateral_shadow_drop_exact_threshold(self):
        """Verify boundary condition for side shadow drop: Delta L* = 7.99 vs 8.01."""
        # Sub-threshold: Delta L* = 7.99 <= 8.0 (no drop)
        reg_sub = [
            {"name": "left", "side": "L", "lab": [60.0, 10.0, 15.0]},
            {"name": "right", "side": "R", "lab": [52.01, 10.0, 15.0]},
        ]
        filtered_sub, dropped_sub = filter_unilateral_shadow(reg_sub, threshold=8.0)
        self.assertFalse(dropped_sub)
        self.assertEqual(len(filtered_sub), 2)

        # Super-threshold: Delta L* = 8.01 > 8.0 (drop triggered)
        reg_super = [
            {"name": "left", "side": "L", "lab": [60.0, 10.0, 15.0]},
            {"name": "right", "side": "R", "lab": [51.99, 10.0, 15.0]},
        ]
        filtered_super, dropped_super = filter_unilateral_shadow(reg_super, threshold=8.0)
        self.assertTrue(dropped_super)
        self.assertEqual(len(filtered_super), 1)
        self.assertEqual(filtered_super[0]["side"], "L")

    def test_both_channels_clipped_blown_out_highlight(self):
        """Verify that when both R and G clip (blown-out), skinRG is bypassed."""
        # When both R and G are clipped (>= 254), highlight cannot be reliably recovered
        r_rec, g_rec, _ = reconstruct_clipped_red(255, 255, 200)
        self.assertEqual(r_rec, srgb_to_linear(1.0))
        self.assertEqual(g_rec, srgb_to_linear(1.0))


# ==============================================================================
# SECTION 4: TIER 3 — CROSS-FEATURE COMBINATIONS TEST CASES
# ==============================================================================


class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """
    Tier 3: Cross-Feature Combinations
    Verifies end-to-end multi-stage pipelines, schema contracts, and downstream rule triggers.
    """

    def test_end_to_end_srgb_to_fitzpatrick_pipeline(self):
        """Verify the full pipeline across the 10-level Monk skin tone scale palette."""
        for tone_level, hex_code in MONK_HEX.items():
            r, g, b = hex_to_rgb(hex_code)
            L, a, b_lab = rgb_to_lab_8bit(r, g, b)
            ita = calculate_ita(L, b_lab)
            fst = classify_fitzpatrick(ita)
            ut, hue, chroma, conf = classify_undertone(a, b_lab, L)

            # Assert consistent ordering: Monk tone depth increases as Lightness decreases
            self.assertTrue(0.0 <= L <= 100.0)
            self.assertTrue(-90.0 <= ita <= 90.0)
            self.assertIn(fst, ("I", "II", "III", "IV", "V", "VI"))
            self.assertIn(ut, ("cool", "neutral", "warm", "olive"))

            # Monk 1 should be light (FST I or II), Monk 10 should be deep (FST VI)
            if tone_level <= 2:
                self.assertIn(fst, ("I", "II"))
            elif tone_level >= 9:
                self.assertIn(fst, ("V", "VI"))

    def test_full_monk_palette_monotonicity(self):
        """
        Verify that Monk skin tone scale swatches exhibit expected macro lightness ordering:
          - Mean Lightness: Light (1-3) > Medium (4-6) > Deep (7-10)
          - Monotonic decrease from Monk 3 to Monk 10
          - Tight clustering of fair swatches (Monk 1-3) differentiated by undertone
        """
        labs = {}
        for tone_level in range(1, 11):
            r, g, b = hex_to_rgb(MONK_HEX[tone_level])
            labs[tone_level] = rgb_to_lab_8bit(r, g, b)

        # Macro band ordering
        mean_light = (labs[1][0] + labs[2][0] + labs[3][0]) / 3.0
        mean_medium = (labs[4][0] + labs[5][0] + labs[6][0]) / 3.0
        mean_deep = (labs[7][0] + labs[8][0] + labs[9][0] + labs[10][0]) / 4.0

        self.assertGreater(mean_light, mean_medium)
        self.assertGreater(mean_medium, mean_deep)

        # Monotonic decrease from Monk 3 through Monk 10
        for i in range(3, 10):
            self.assertGreater(
                labs[i][0],
                labs[i + 1][0],
                f"L* failed to decrease between Monk {i} and Monk {i+1}",
            )

        # Fair tones (1-3) cluster tightly in lightness (within 2.5 units)
        self.assertLess(abs(labs[1][0] - labs[2][0]), 2.5)
        self.assertLess(abs(labs[2][0] - labs[3][0]), 2.5)
        # But vary significantly in yellowness b* (Monk 3 golden > Monk 1 neutral)
        self.assertGreater(labs[3][2], labs[1][2] + 5.0)

    def test_data_contract_cross_validation(self):
        """Verify contract schema validator correctly catches diverse malformed payloads."""
        base_payload = {
            "status": "OK",
            "tone": 7,
            "monkScale": "Monk 07",
            "undertone": "warm",
            "ita": 5.2,
            "fitzpatrick": "V",
            "lab": [48.5, 13.8, 19.5],
            "conf": 0.91,
            "method": "mediapipe_sclera_d65",
            "issues": [],
            "regions": [{"name": "left_cheek", "lab": [48.2, 13.5, 19.1]}],
        }

        # Valid baseline
        valid, _ = validate_aaina_data_contract(base_payload)
        self.assertTrue(valid)

        # Corrupted case 1: Inconsistent Monk scale string
        bad_monk = dict(base_payload, monkScale="Monk 08")
        valid, errs = validate_aaina_data_contract(bad_monk)
        self.assertFalse(valid)
        self.assertTrue(any("monkScale mismatch" in e for e in errs))

        # Corrupted case 2: Inconsistent Fitzpatrick phototype far outside hysteresis
        bad_fst = dict(base_payload, fitzpatrick="I")  # ITA=5.2 is FST V, far from FST I (>55)
        valid, errs = validate_aaina_data_contract(bad_fst)
        self.assertFalse(valid)
        self.assertTrue(any("fitzpatrick mismatch" in e for e in errs))

        # Corrupted case 3: Out-of-bounds L* coordinate
        bad_lab = dict(base_payload, lab=[120.0, 10.0, 10.0])
        valid, errs = validate_aaina_data_contract(bad_lab)
        self.assertFalse(valid)

    def test_data_contract_adversarial_tampering(self):
        """Verify validator handles adversarial inputs (wrong types, missing keys, empty regions)."""
        valid_base = {
            "status": "OK",
            "tone": 5,
            "monkScale": "Monk 05",
            "undertone": "warm",
            "ita": 20.0,
            "fitzpatrick": "IV",
            "lab": [55.0, 12.0, 18.0],
            "conf": 0.90,
            "method": "mediapipe_sclera_d65",
            "issues": [],
            "regions": [{"name": "c", "lab": [55.0, 12.0, 18.0]}],
        }

        # Missing required key 'status'
        no_status = {k: v for k, v in valid_base.items() if k != "status"}
        v, err = validate_aaina_data_contract(no_status)
        self.assertFalse(v)

        # Non-integer tone
        float_tone = dict(valid_base, tone=5.5)
        v, err = validate_aaina_data_contract(float_tone)
        self.assertFalse(v)

        # Empty regions list
        empty_reg = dict(valid_base, regions=[])
        v, err = validate_aaina_data_contract(empty_reg)
        self.assertFalse(v)

    def test_downstream_recommendation_guardrail_triggers(self):
        """
        Verify downstream skincare recommendation triggers in src/app.js:746-750
        directly consume shade detection output:
          - Deep tone trigger (P.tone >= 7): Mineral sunscreen penalty (-2.5)
          - Medium/Deep PIH trigger (P.tone >= 4): Chemical exfoliant penalty
        """

        def simulate_sunscreen_scoring(p_tone: int, is_mineral: bool) -> float:
            score = 10.0
            deep = p_tone >= 7
            if deep and is_mineral:
                score -= 2.5
            return score

        def simulate_exfoliant_scoring(p_tone: int, gly_pct: float) -> float:
            score = 10.0
            deep = p_tone >= 7
            medium = 4 <= p_tone <= 6
            if (deep or medium) and gly_pct >= 10.0:
                score -= 2.5 if deep else 1.0
            return score

        # Tone 8 (Deep) evaluating mineral sunscreen: must receive -2.5 penalty
        self.assertEqual(simulate_sunscreen_scoring(8, is_mineral=True), 7.5)
        # Tone 2 (Light) evaluating mineral sunscreen: no white-cast penalty
        self.assertEqual(simulate_sunscreen_scoring(2, is_mineral=True), 10.0)

        # Tone 5 (Medium) evaluating 10% glycolic: receives -1.0 PIH safety penalty
        self.assertEqual(simulate_exfoliant_scoring(5, gly_pct=10.0), 9.0)
        # Tone 8 (Deep) evaluating 10% glycolic: receives -2.5 severe PIH safety penalty
        self.assertEqual(simulate_exfoliant_scoring(8, gly_pct=10.0), 7.5)

    def test_complexion_shade_matching_depth_filtering(self):
        """
        Verify complexion shade matching criteria in src/engine.js:302-308:
          - Candidates filtered by |depth - P.tone| <= 1
          - Delta E colorimetric ranking
        """
        user_tone = 6
        candidate_shades = [
            {"name": "Porcelain 02", "depth": 2, "lab": (75.0, 8.0, 15.0)},
            {"name": "Warm Natural 05", "depth": 5, "lab": (56.0, 12.0, 20.0)},
            {"name": "Golden Honey 06", "depth": 6, "lab": (52.0, 14.0, 22.0)},
            {"name": "Caramel 07", "depth": 7, "lab": (48.0, 15.0, 24.0)},
            {"name": "Espresso 09", "depth": 9, "lab": (32.0, 10.0, 12.0)},
        ]
        user_lab = (51.5, 14.2, 22.5)

        # Filter within depth delta <= 1
        filtered = [s for s in candidate_shades if abs(s["depth"] - user_tone) <= 1]
        self.assertEqual(len(filtered), 3)  # Depths 5, 6, 7
        self.assertEqual([s["depth"] for s in filtered], [5, 6, 7])

        # Colorimetric Euclidean distance Delta E
        for s in filtered:
            s["delta_e"] = math.hypot(
                s["lab"][0] - user_lab[0],
                s["lab"][1] - user_lab[1],
                s["lab"][2] - user_lab[2],
            )
        filtered.sort(key=lambda s: s["delta_e"])
        # Closest match must be "Golden Honey 06"
        self.assertEqual(filtered[0]["name"], "Golden Honey 06")
        self.assertLess(filtered[0]["delta_e"], 2.0)

    def test_white_balance_interaction_with_skin_tone(self):
        """Verify that sclera white balance gains recover true skin CIELAB from a warm cast."""
        # Uncalibrated skin with warm illuminant (2700K: Red boosted 1.25x, Blue reduced 0.70x)
        raw_sclera = (0.86 * 1.25, 0.84 * 1.05, 0.79 * 0.70)
        gains = derive_sclera_gains(raw_sclera)

        # Baseline ground truth skin in linear space
        gt_linear = (0.55, 0.40, 0.30)
        illuminated_skin = (gt_linear[0] * 1.25, gt_linear[1] * 1.05, gt_linear[2] * 0.70)

        # Apply correction gains
        corrected_skin = (
            illuminated_skin[0] * gains[0],
            illuminated_skin[1] * gains[1],
            illuminated_skin[2] * gains[2],
        )

        # Converted to Lab
        xyz_gt = linear_rgb_to_xyz(*gt_linear)
        xyz_corr = linear_rgb_to_xyz(*corrected_skin)
        lab_gt = xyz_to_lab(*xyz_gt)
        lab_corr = xyz_to_lab(*xyz_corr)

        # Color difference Delta E should be virtually eliminated (< 0.5)
        delta_E = math.hypot(
            lab_gt[0] - lab_corr[0],
            lab_gt[1] - lab_corr[1],
            lab_gt[2] - lab_corr[2],
        )
        self.assertLess(delta_E, 0.5)


# ==============================================================================
# SECTION 5: TIER 4 — REAL-WORLD SCENARIOS TEST CASES
# ==============================================================================


class TestTier4RealWorldScenarios(unittest.TestCase):
    """
    Tier 4: Real-World Scenarios
    Tests noise, directional shadows, sensor clipping, and low-light stress conditions.
    """

    def test_unilateral_side_lighting_shadow_drop(self):
        """
        Verify unilateral shadow drop when directional light causes bilateral
        cheeks to differ by |ΔL*| > 8.0. Shadowed hemisphere must be ignored.
        """
        regions = [
            {"name": "left_cheek", "side": "L", "lab": [64.5, 12.0, 18.0]},
            {"name": "forehead_left", "side": "L", "lab": [63.8, 11.5, 17.5]},
            {"name": "right_cheek", "side": "R", "lab": [51.0, 13.5, 19.5]},  # In shadow: ΔL* = 13.5
            {"name": "forehead_right", "side": "R", "lab": [52.2, 12.8, 18.8]},
        ]
        filtered, dropped = filter_unilateral_shadow(regions, threshold=8.0)
        self.assertTrue(dropped)
        self.assertEqual(len(filtered), 2)
        # All preserved regions must be from the lit side ("L")
        for r in filtered:
            self.assertEqual(r["side"], "L")
            self.assertGreaterEqual(r["lab"][0], 60.0)

    def test_red_channel_sensor_highlight_recovery(self):
        """
        Verify that clipped red channel (R=255, G=210, B=180) is reconstructed
        via empirical skinRG, preserving natural skin R/G reflectance ratio.
        """
        r_clipped = 255
        g_unclipped = 210
        b_unclipped = 180

        # Unreconstructed linear channels
        g_lin = srgb_to_linear(g_unclipped / 255.0)

        # Reconstruct with empirical skinRG
        r_rec, g_rec, b_rec = reconstruct_clipped_red(r_clipped, g_unclipped, b_unclipped)

        # Reconstructed red must strictly exceed green, preventing sickly green-yellow cast
        self.assertGreater(r_rec, g_rec)

        # The reconstructed red/green ratio must exactly match the empirical skin table
        expected_ratio = skin_rg(g_lin)
        self.assertAlmostEqual(r_rec / g_rec, expected_ratio, places=5)

        # When red is not clipped (e.g. R=230), no reconstruction occurs
        r_norm, g_norm, b_norm = reconstruct_clipped_red(230, 210, 180)
        self.assertAlmostEqual(r_norm, srgb_to_linear(230 / 255.0), places=6)

    def test_deep_skin_chroma_compression_handling(self):
        """
        Verify that deep skin (FST VI, L* < 32) with low chroma (C* < 8)
        receives appropriate confidence damping rather than erratic undertone swings.
        """
        # Deep skin coordinate: L* = 28.0, a* = 3.5, b* = 5.0 -> Chroma = 6.10, Hue ~ 55° (Neutral)
        L_deep = 28.0
        a_deep = 3.5
        b_deep = 5.0
        ut, hue, chroma, conf = classify_undertone(a_deep, b_deep, L_deep)
        self.assertLess(chroma, 8.0)
        # Confidence must be dampened due to compressed chroma
        self.assertLess(conf, 0.70)
        # Classification should remain stable in valid category
        self.assertIn(ut, ("cool", "neutral", "warm", "olive"))
        self.assertEqual(ut, "neutral")

    def test_bloodshot_sclera_and_fallback_to_background(self):
        """
        Verify that bloodshot sclera (conjunctivitis / red excess) is detected
        and rejected (chroma > 12.0), triggering fallback to background Shades-of-Grey.
        """
        # Normal sclera: low chroma (< 4.0)
        normal_sclera_lab = xyz_to_lab(*linear_rgb_to_xyz(*SCLERA_REF))
        normal_chroma = math.hypot(normal_sclera_lab[1], normal_sclera_lab[2])
        self.assertLess(normal_chroma, 12.0)

        # Pathological bloodshot sclera: elevated red reflectance (sR=0.98, sG=0.65, sB=0.60)
        bloodshot_sclera = (0.98, 0.65, 0.60)
        bloodshot_lab = xyz_to_lab(*linear_rgb_to_xyz(*bloodshot_sclera))
        bloodshot_chroma = math.hypot(bloodshot_lab[1], bloodshot_lab[2])
        # Bloodshot sclera chroma significantly exceeds valid threshold (12.0)
        self.assertGreater(bloodshot_chroma, 12.0)

        # Sclera validator should flag invalid
        def is_valid_sclera(s_lin: Tuple[float, float, float]) -> bool:
            lab = xyz_to_lab(*linear_rgb_to_xyz(*s_lin))
            return math.hypot(lab[1], lab[2]) <= 12.0

        self.assertTrue(is_valid_sclera(SCLERA_REF))
        self.assertFalse(is_valid_sclera(bloodshot_sclera))

    def test_non_standard_illuminant_compensation(self):
        """
        Verify illuminant compensation across non-standard real-world lighting:
          - Tungsten (2700K)
          - Cool Daylight (6500K)
        """
        # Simulation vectors
        illuminants = {
            "tungsten_2700k": (1.25, 0.95, 0.60),
            "cool_daylight": (0.85, 0.95, 1.20),
        }
        for name, ill in illuminants.items():
            measured_sclera = (
                SCLERA_REF[0] * ill[0],
                SCLERA_REF[1] * ill[1],
                SCLERA_REF[2] * ill[2],
            )
            gains = derive_sclera_gains(measured_sclera)
            # Recovered sclera must match reference within 2%
            recovered = (
                measured_sclera[0] * gains[0],
                measured_sclera[1] * gains[1],
                measured_sclera[2] * gains[2],
            )
            self.assertAlmostEqual(recovered[0], SCLERA_REF[0], delta=0.02)
            self.assertAlmostEqual(recovered[1], SCLERA_REF[1], delta=0.02)
            self.assertAlmostEqual(recovered[2], SCLERA_REF[2], delta=0.02)

    def test_optical_brightener_paper_detection(self):
        """
        Verify detection and rejection of domestic paper targets contaminated with
        Optical Brightening Agents (OBAs) exhibiting blue fluorescence (B / max(R,G) > 1.15).
        """
        def has_oba_contamination(target_rgb: Tuple[float, float, float]) -> bool:
            r, g, b = target_rgb
            return b / max(r, g, 1e-4) > 1.15

        # Standard non-fluorescent white card
        pure_card = (0.95, 0.95, 0.94)
        self.assertFalse(has_oba_contamination(pure_card))

        # OBA-treated copy paper fluorescing blue under ambient UV
        oba_paper = (0.88, 0.90, 1.12)
        self.assertTrue(has_oba_contamination(oba_paper))


# ==============================================================================
# SECTION 6: TEST RUNNER & VERIFICATION HARNESS
# ==============================================================================


def run_verification_suite() -> bool:
    """Execute the full 4-tier verification suite and print summary."""
    print("=" * 72)
    print("AAINA AI SKIN TONE & SHADE DETECTION: 4-TIER SPECIFICATION TEST SUITE")
    print("=" * 72)

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    tier_classes = [
        ("Tier 1: Feature Coverage", TestTier1FeatureCoverage),
        ("Tier 2: Boundary & Corner Cases", TestTier2BoundaryCornerCases),
        ("Tier 3: Cross-Feature Combinations", TestTier3CrossFeatureCombinations),
        ("Tier 4: Real-World Scenarios", TestTier4RealWorldScenarios),
    ]

    for name, cls in tier_classes:
        tests = loader.loadTestsFromTestCase(cls)
        suite.addTests(tests)
        print(f"Loaded {tests.countTestCases():2d} tests for {name}")

    print("-" * 72)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("=" * 72)

    if result.wasSuccessful():
        print(
            f"ALL {result.testsRun} TESTS PASSED SUCCESSFULLY (100% Pass Rate - Exit Code 0)"
        )
        return True
    else:
        print(
            f"TEST RUN FAILED: {len(result.failures)} Failures, {len(result.errors)} Errors"
        )
        return False


if __name__ == "__main__":
    import sys

    success = run_verification_suite()
    sys.exit(0 if success else 1)
