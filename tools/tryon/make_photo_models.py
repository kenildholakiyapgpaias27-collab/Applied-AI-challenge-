#!/usr/bin/env python3
"""Model faces for the virtual try-on, cut from two reference collages (4 women, 4 men).

    python3 tools/tryon/make_photo_models.py WOMEN_COLLAGE MEN_COLLAGE

WOMEN_COLLAGE: the 736x1104 "Different tones, same beautiful skin" grid (3x2 portraits).
MEN_COLLAGE:   the 736x736 "Colours that suit your skin tone" grid (5 portraits in a row).
The collages themselves are not stored in the repo.

For each chosen portrait: crop a 4:5 frame inside its panel (no captions), enlarge to 640x800,
find the 478 MediaPipe face landmarks on the final image, and read the skin tone from the cheeks.
Writes data/model_faces/*.jpg, data/model_faces.json and data/model_faces_landmarks.json.
Needs: pillow numpy mediapipe (uses backend/models/face_landmarker.task).
"""
import colorsys, json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core import base_options as bo

ROOT = Path(__file__).resolve().parents[2]
OUT_W, OUT_H = 640, 800
# panels (x0, y0, x1, y1) in the source collage, 4:5, inside the photo and above its caption
WOMEN = [("w-fair", "Fair", (31, 193, 241, 455)), ("w-medium", "Medium", (498, 193, 708, 455)),
         ("w-tan", "Tan", (31, 593, 241, 855)), ("w-deep", "Deep", (265, 593, 475, 855))]
MEN = [("m-fair", "Fair", (25, 145, 159, 313)), ("m-medium", "Medium", (162, 145, 296, 313)),
       ("m-tan", "Tan", (436, 145, 570, 313)), ("m-deep", "Deep", (573, 145, 707, 313))]
# Aaina tone swatches and undertone hue bands, as in src/engine.js
MONK_HEX = {1: "#f6ede4", 2: "#f3e7db", 3: "#f7ead0", 4: "#eadaba", 5: "#d7bd96", 6: "#a07e56", 7: "#825c43", 8: "#604134", 9: "#3a312a", 10: "#292420"}
COOL_BELOW, WARM_FROM, OLIVE_FROM = 50, 60, 72


def lab(rgb):
    def lin(c):
        c /= 255; return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = map(lin, rgb)
    x, y, z = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047, 0.2126 * r + 0.7152 * g + 0.0722 * b, (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (841 / 108) * t + 4 / 29
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def hexrgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def main(women_path, men_path):
    det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=bo.BaseOptions(model_asset_path=str(ROOT / "backend/models/face_landmarker.task")), num_faces=1))
    out_dir = ROOT / "data/model_faces"; out_dir.mkdir(exist_ok=True)
    for old in out_dir.glob("*.jpg"): old.unlink()
    faces, marks = [], {}
    for gender, path, picks in (("woman", women_path, WOMEN), ("man", men_path, MEN)):
        src = Image.open(path).convert("RGB")
        for fid, name, box in picks:
            im = src.crop(box).resize((OUT_W, OUT_H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
            res = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(im)))
            if not res.face_landmarks: sys.exit(f"no face found in {fid}")
            pts = [[round(p.x, 5), round(p.y, 5)] for p in res.face_landmarks[0]]
            a = np.asarray(im, float)
            px = np.concatenate([a[int(y * OUT_H) - 6:int(y * OUT_H) + 6, int(x * OUT_W) - 6:int(x * OUT_W) + 6].reshape(-1, 3)
                                 for x, y in (pts[i] for i in (205, 425, 50, 280))])
            rgb = tuple(int(v) for v in np.median(px, axis=0))
            L, A, B = lab(rgb)
            monk = min(MONK_HEX, key=lambda t: math.dist(lab(hexrgb(MONK_HEX[t])), (L, A, B)))
            hue = math.degrees(math.atan2(B, A))
            ut = "cool" if hue < COOL_BELOW else "neutral" if hue < WARM_FROM else "warm" if hue < OLIVE_FROM else "olive"
            im.save(out_dir / f"{fid}.jpg", quality=90)
            faces.append({"id": fid, "label": f"{name} · {gender}", "gender": gender, "hex": "#%02x%02x%02x" % rgb, "monk": monk,
                          "undertone": ut, "file": f"data/model_faces/{fid}.jpg"})
            marks[fid] = pts
            print(f"{fid:9s} {faces[-1]['hex']}  Monk {monk}  {ut:7s}  hue {hue:.0f}")
    faces.sort(key=lambda f: (f["gender"] != "woman", f["monk"]))
    (ROOT / "data/model_faces.json").write_text(json.dumps({
        "source": "Cropped by tools/tryon/make_photo_models.py from two reference collages supplied by the team "
                  "(4 women, 4 men). Source and usage rights of the collages to be confirmed before public release.",
        "size": [OUT_W, OUT_H], "faces": faces}, indent=1, ensure_ascii=False) + "\n")
    (ROOT / "data/model_faces_landmarks.json").write_text(json.dumps(marks, separators=(",", ":")))


if __name__ == "__main__":
    main(*sys.argv[1:3])
