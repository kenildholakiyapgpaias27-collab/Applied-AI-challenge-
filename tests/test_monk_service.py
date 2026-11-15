"""Unit and Integration Tests for Google Monk Skin Tone Backend Service."""

import base64
import io
import sys
from pathlib import Path
import unittest

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from PIL import Image
from fastapi.testclient import TestClient

from backend.app import app
from backend.monk_service import (
    MONK_PALETTE,
    calculate_ita,
    classify_fitzpatrick,
    classify_undertone,
    delta_e_76,
    hex_to_rgb,
    match_monk_tone,
    process_image_for_monk_tone,
    rgb_to_lab_8bit,
)


class TestMonkSkinToneService(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "monk-skin-tone-engine")

    def test_monk_palette_endpoint(self):
        response = self.client.get("/api/monk-palette")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["levels_count"], 10)
        self.assertIn("palette", data)
        self.assertEqual(len(data["palette"]), 10)

    def test_monk_scale_all_ten_tones_exact_match(self):
        """Ensure every official Google Monk swatch maps back to its exact tone."""
        for tone_idx, info in MONK_PALETTE.items():
            r, g, b = hex_to_rgb(info["hex"])
            lab = rgb_to_lab_8bit(r, g, b)
            result = match_monk_tone(lab)

            self.assertEqual(
                result["tone"],
                tone_idx,
                f"Monk {tone_idx} ({info['hex']}) failed to map to itself: got {result['tone']}",
            )
            self.assertEqual(result["monk_name"], info["name"])
            self.assertAlmostEqual(result["delta_e"], 0.0, places=1)
            self.assertGreaterEqual(result["confidence"], 0.95)

    def test_classify_tone_endpoint_with_hex(self):
        # Test Monk 06 (#a07e56)
        response = self.client.post("/api/classify-tone", json={"hex": "#a07e56"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["tone"], 6)
        self.assertEqual(data["monk_name"], "Monk 06")
        self.assertEqual(data["band"], "Medium-Deep")
        self.assertEqual(data["undertone"], "warm")

    def test_classify_tone_endpoint_with_rgb(self):
        # Test Monk 01 (#f6ede4 -> [246, 237, 228])
        response = self.client.post("/api/classify-tone", json={"rgb": [246, 237, 228]})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["tone"], 1)
        self.assertEqual(data["monk_name"], "Monk 01")
        self.assertIn(data["fitzpatrick_scale"], ["I", "II"])

    def test_detect_monk_tone_from_synthetic_image(self):
        """Generate a synthetic test image with a skin-toned oval on neutral background."""
        w, h = 300, 400
        img = Image.new("RGB", (w, h), color=(180, 180, 180))  # Neutral gray background

        # Paint an oval in Monk 05 (#d7bd96 -> 215, 189, 150)
        pixels = img.load()
        cx, cy = w / 2.0, h / 2.0
        rx, ry = w * 0.25, h * 0.30
        for y in range(h):
            for x in range(w):
                if ((x - cx) ** 2 / rx**2) + ((y - cy) ** 2 / ry**2) <= 1.0:
                    pixels[x, y] = (215, 189, 150)

        # Convert to base64
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")

        response = self.client.post("/api/detect-monk-tone", json={"image": b64_str})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "OK")
        self.assertEqual(data["tone"], 5)
        self.assertEqual(data["monk_name"], "Monk 05")
        self.assertEqual(data["band"], "Medium")

    def test_recapture_on_black_or_invalid_image(self):
        """Verify that an image with no face/skin triggers RECAPTURE cleanly."""
        img = Image.new("RGB", (200, 200), color=(10, 10, 10))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")

        response = self.client.post("/api/detect-monk-tone", json={"image": b64_str})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "RECAPTURE")
        self.assertIn("issue", data)

    def test_white_card_calibration_workflow(self):
        """Verify that an image featuring a white reference card triggers D65 calibration."""
        from PIL import ImageDraw
        # Create an image with skin oval and a white reference card below
        img = Image.new("RGB", (400, 500), color=(120, 100, 90))
        draw = ImageDraw.Draw(img)
        # Skin center (Monk 05 tone: #ce9e81)
        draw.ellipse([140, 80, 260, 260], fill=(206, 158, 129))
        # White reference card in bottom third (under warm indoor light: #f5dfc2)
        draw.rectangle([80, 360, 320, 460], fill=(245, 223, 194))

        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")

        response = self.client.post("/api/detect-monk-tone", json={"image": b64_str})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "OK")
        self.assertTrue(data.get("white_card_calibrated"))
        self.assertGreaterEqual(data.get("confidence", 0), 0.95)
        self.assertIn("card_illuminant_rgb", data)


if __name__ == "__main__":
    unittest.main()
