#!/usr/bin/env python3
"""Unit tests for the virtual try-on data: demo colours and model faces, then the JS colour maths.

    python3 tests/tryon_unit_test.py

No browser needed. The colour/blend tests run with Node (tests/tryon_colour_test.js) if it is installed.
"""
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"   {detail}"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gen = load("make_demo_colours", ROOT / "tools/tryon/make_demo_colours.py")
catalogue_text = (ROOT / "data/catalogue.json").read_text(encoding="utf-8")
catalogue = json.loads(catalogue_text)
demo = json.loads((ROOT / "data/demo_colours.json").read_text(encoding="utf-8"))

# ---- demo colour generator ----
a, b = gen.build(catalogue), gen.build(json.loads(catalogue_text))
check("generator is deterministic (two runs identical)", json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True))
check("committed demo_colours.json matches the generator", json.dumps(a, sort_keys=True) == json.dumps(demo, sort_keys=True),
      "re-run python3 tools/tryon/make_demo_colours.py")
shuffled = list(reversed(catalogue))
check("output does not depend on catalogue order", json.dumps(gen.build(shuffled), sort_keys=True) == json.dumps(a, sort_keys=True))

want = {p["id"] for p in catalogue if p["c"] in gen.CATS}
check("every Lipstick, Blush and Kajal / eyeliner product has demo colours", set(demo["products"]) == want,
      f"{len(want ^ set(demo['products']))} mismatched")
counts = {c: sum(1 for v in demo["products"].values() if v["c"] == c) for c in gen.CATS}
check("product counts: 60 lipsticks, 15 blushes, 25 kajal/liners", counts == {"Lipstick": 60, "Blush": 15, "Kajal / eyeliner": 25}, counts)
shades = [s for v in demo["products"].values() for s in v["shades"]]
check("4 to 8 shades per product", all(4 <= len(v["shades"]) <= 8 for v in demo["products"].values()))
check("every hex is a valid #rrggbb", all(re.fullmatch(r"#[0-9a-f]{6}", s["hex"]) for s in shades))
check("every demo shade carries demo: true", all(s.get("demo") is True for s in shades) and demo.get("demo") is True)
check("every shade has a name and a known finish", all(s["name"] and s["finish"] in {"matte", "satin", "creme", "gloss", "sheer", "dewy", "shimmer"} for s in shades))
check("no duplicate shade names within a product", all(len({s["name"] for s in v["shades"]}) == len(v["shades"]) for v in demo["products"].values()))
lum = lambda h: sum(int(h[i:i + 2], 16) for i in (1, 3, 5)) / 3
check("kajal/liner shades are dark", all(lum(s["hex"]) < 110 for v in demo["products"].values() if v["c"] == "Kajal / eyeliner" for s in v["shades"]))

# ---- no demo data leaks into real data ----
names = {s["name"] for s in shades}
hexes = {s["hex"] for s in shades}
check("catalogue.json has no shade arrays for demo-coloured products",
      all("s" not in p for p in catalogue if p["c"] in gen.CATS))
check("catalogue.json contains no demo shade names", not any(n in catalogue_text for n in names),
      [n for n in names if n in catalogue_text][:3])
check("catalogue.json contains no demo flag", '"demo"' not in catalogue_text)
seed = ROOT / "supabase/seed.sql"
if seed.exists():
    seed_text = seed.read_text(encoding="utf-8")
    check("seed.sql contains no demo shade names or colours", not any(n in seed_text for n in names) and not any(h in seed_text.lower() for h in hexes))
db_src = (ROOT / "src/db.js").read_text(encoding="utf-8")
check("database code never references the demo colours", "TRYON_DEMO" not in db_src and "demo_colours" not in db_src)
check("seed tool never reads demo_colours.json", "demo_colours" not in (ROOT / "tools/seed_catalogue.py").read_text(encoding="utf-8"))

# ---- model faces ----
faces = json.loads((ROOT / "data/model_faces.json").read_text(encoding="utf-8"))
lms = json.loads((ROOT / "data/model_faces_landmarks.json").read_text(encoding="utf-8"))
want_hex = ["#e6d0cd", "#f3c6a8", "#d39b78", "#ab6f51", "#91604b", "#483026"]
check("six model faces with the given base tones, fair to very deep", [f["hex"] for f in faces["faces"]] == want_hex, [f["hex"] for f in faces["faces"]])
check("each face has id, label, hex, Monk tone, undertone and image file",
      all(set(f) >= {"id", "label", "hex", "monk", "undertone", "file"} and f["undertone"] in {"warm", "cool", "neutral", "olive"} and 1 <= f["monk"] <= 10 for f in faces["faces"]))
check("Monk tones rise from fair to very deep", [f["monk"] for f in faces["faces"]] == sorted(f["monk"] for f in faces["faces"]))
check("each face has 478 landmarks inside the image", all(len(lms[f["id"]]) == 478 and all(0 <= x <= 1 and 0 <= y <= 1 for x, y in lms[f["id"]]) for f in faces["faces"]))
check("each face image exists", all((ROOT / f["file"]).exists() for f in faces["faces"]))
check("faces are rendered, not photographs", "No photographs of real people" in faces["source"])
check("old doll faces are gone", not (ROOT / "data/tryon_models.json").exists() and not (ROOT / "data/tryon_models").exists())
try:
    from PIL import Image
    import numpy as np
    def mid_tone(f):
        im = np.asarray(Image.open(ROOT / f["file"]).convert("RGB"), float)
        lm = lms[f["id"]]; h, w = im.shape[:2]
        pts = [lm[i] for i in (205, 425, 50, 280)]
        return np.median(np.concatenate([im[int(y * h) - 4:int(y * h) + 4, int(x * w) - 4:int(x * w) + 4].reshape(-1, 3) for x, y in pts]), axis=0)
    def dist(f):
        c = mid_tone(f); b = [int(f["hex"][i:i + 2], 16) for i in (1, 3, 5)]
        return float(np.abs(c - b).mean())
    d = {f["id"]: round(dist(f), 1) for f in faces["faces"]}
    check("rendered cheeks sit near each face's base tone (mean channel gap < 22)", all(v < 22 for v in d.values()), d)
except ImportError:
    print("SKIP base-tone check: Pillow/numpy not installed")

# ---- JS colour maths ----
node = shutil.which("node")
if node:
    r = subprocess.run([node, str(ROOT / "tests/tryon_colour_test.js")], capture_output=True, text=True)
    print(r.stdout.rstrip())
    check("JS colour/blend tests (node)", r.returncode == 0, r.stderr[-400:])
else:
    print("SKIP JS colour/blend tests: node not installed")

print(f"\n{sum(RESULTS)}/{len(RESULTS)} passed")
sys.exit(0 if all(RESULTS) else 1)
