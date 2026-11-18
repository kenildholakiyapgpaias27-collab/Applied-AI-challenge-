#!/usr/bin/env python3
"""Generate FICTIONAL in-house product studies for the demo catalogue (every skincare product).

    python3 tools/make_sample_studies.py      # writes data/evidence/sample_product_studies.json

Aaina's products and brands are fictional (PS-14 demo), so they have no real product studies. This makes one
sample "in-house consumer test" per product, the kind of self-reported agreement study brands run, so the demo
can show what such a study looks like. Rules:
- Every study is marked fictional, and the app always badges it "Sample data · fictional".
- No PubMed IDs, DOIs, authors or journals: nothing that could pass for real research.
- Studies describe the fictional PRODUCT only. Real ingredients keep their real evidence
  (data/evidence/actives_timeline.json); no made-up results are attached to an ingredient.
- They never feed the real timeline's numbers, grades, comparisons or illustration.
Deterministic: the same catalogue always gives the same file.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT = json.loads((ROOT / "data/catalogue.json").read_text(encoding="utf-8"))
SKINCARE = {"Serum", "Moisturiser", "Sunscreen", "Cleanser", "Toner", "Exfoliant", "Face mask", "Eye cream", "Spot treatment", "Lip care", "Face oil"}
WEEKS = {"Serum": 8, "Moisturiser": 4, "Sunscreen": 4, "Cleanser": 4, "Toner": 6, "Exfoliant": 8, "Face mask": 4, "Eye cream": 8,
         "Spot treatment": 4, "Lip care": 2, "Face oil": 8}
CITIES = ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata", "Pune", "Hyderabad", "Jaipur"]


def h(pid, salt, lo, hi):
    """deterministic number in [lo, hi] from the product id"""
    x = int(hashlib.sha256(f"{pid}:{salt}".encode()).hexdigest()[:8], 16)
    return lo + x % (hi - lo + 1)


def study(p):
    pid, wk = p["id"], WEEKS[p["c"]]
    concern = (p.get("con") or [None])[0] or ("comfort" if p["c"] == "Sunscreen" else "lips" if p["c"] == "Lip care" else "dehydration")
    if p["c"] == "Sunscreen": concern = "comfort"
    if p["c"] == "Lip care": concern = "lips"
    points = [w for w in (1, 2, 4, 8, 12) if w <= wk and w >= wk / 4][-3:] or [wk]
    if points[-1] != wk: points.append(wk)
    end = h(pid, "end", 64, 88)
    start = max(40, end - h(pid, "gain", 10, 26))
    agree = [round(start + (end - start) * i / max(1, len(points) - 1)) for i in range(len(points))]
    cities = sorted({CITIES[h(pid, f"c{i}", 0, len(CITIES) - 1)] for i in range(3)})
    return {"concern": concern, "n": h(pid, "n", 30, 60), "weeks": points, "agree": agree, "cities": cities,
            "tones": f"{h(pid, 'tlo', 2, 4)}–{h(pid, 'thi', 8, 10)}"}


out = {"fictional": True,
       "label": "Sample data · fictional",
       "about": "Made-up in-house consumer tests for the fictional demo products. Not real research: no real people, no "
                "publication, no citation. Shown only with a 'Sample data · fictional' badge and never used for the evidence-based timeline.",
       "design": "open-label in-house consumer test, self-assessment questionnaire, no comparison group",
       "studies": {p["id"]: study(p) for p in CAT if p["c"] in SKINCARE}}
(ROOT / "data/evidence/sample_product_studies.json").write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
print(f"{len(out['studies'])} fictional product studies written")
