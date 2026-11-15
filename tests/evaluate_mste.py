#!/usr/bin/env python3
"""
AAINA Skin Tone Recognition: Accuracy Evaluation on Google MST-E Dataset.

Evaluates the AAINA backend Monk Skin Tone engine against the official
Google Monk Skin Tone Examples (MST-E) dataset — real photos with ground-truth
MST labels annotated by Dr. Monk himself.

Usage:
    /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 tests/evaluate_mste.py
"""
from __future__ import annotations
import csv
import sys
import time
import collections
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
MST_E_DIR = Path("/Users/shreyanshshailesh/Downloads/mst-e_data")
sys.path.insert(0, str(ROOT_DIR))

from backend.monk_service import process_image_for_monk_tone

DETAILS_CSV = MST_E_DIR / "mst-e_image_details.csv"
GOLDEN_CSV  = MST_E_DIR / "golden_and_adversarial_mst-e_image_ids.csv"


def load_dataset(max_per_mst: int = 20, pose_filter: str = "facing_camera") -> list[dict]:
    """
    Load a balanced, face-forward sample of the MST-E dataset.
    max_per_mst: cap per MST level so deep/light tones aren't over- or under-represented.
    """
    rows = []
    with open(DETAILS_CSV, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append({k.strip(): v.strip() for k, v in r.items()})

    # Keep only JPG, face-forward, unmasked images
    valid = [
        r for r in rows
        if r["image_ID"].lower().endswith(".jpg")
        and r["mask"] == "0"
        and r["pose"] in {"facing_camera", "frontal"}
    ]

    # Balance per MST tone
    by_mst: dict[str, list] = collections.defaultdict(list)
    for r in valid:
        by_mst[r["MST"]].append(r)

    balanced = []
    for mst_val in sorted(by_mst.keys(), key=int):
        entries = by_mst[mst_val]
        # Prefer well-lit over poorly-lit
        well = [e for e in entries if e["lighting"] == "well_lit"]
        poor = [e for e in entries if e["lighting"] == "poorly_lit"]
        ordered = well + poor
        balanced.extend(ordered[:max_per_mst])

    return balanced


def load_golden_set() -> dict[str, dict]:
    """Load the official 'golden' (ideal) and 'adversarial' (not-ideal) image sets."""
    golden_map = {}
    with open(GOLDEN_CSV, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            r = {k.strip(): v.strip() for k, v in r.items()}
            golden_map[r["golden_image_id"]] = {"subject": r["subject"], "type": "golden"}
            golden_map[r["not_ideal_image_id"]] = {"subject": r["subject"], "type": "adversarial"}
    return golden_map


def evaluate(samples: list[dict], label: str) -> dict:
    exact = within1 = within2 = no_face = errors = 0
    per_mst: dict[int, dict] = {t: {"exact": 0, "within1": 0, "within2": 0, "total": 0, "failed": 0} for t in range(1, 11)}
    per_lighting: dict[str, dict] = {}
    all_results = []

    total = len(samples)
    print(f"\n{'='*72}")
    print(f"  Evaluating: {label} ({total} images)")
    print(f"{'='*72}")

    for idx, sample in enumerate(samples, 1):
        subject = sample["subject_name"]
        mst_gt  = int(sample["MST"])
        fname   = sample["image_ID"]
        light   = sample["lighting"]
        img_path = MST_E_DIR / subject / fname

        per_lighting.setdefault(light, {"exact": 0, "within1": 0, "within2": 0, "total": 0})
        per_lighting[light]["total"] += 1
        per_mst[mst_gt]["total"] += 1

        if not img_path.exists():
            errors += 1
            per_mst[mst_gt]["failed"] += 1
            all_results.append({"file": fname, "gt": mst_gt, "pred": None, "status": "FILE_MISSING", "lighting": light})
            continue

        try:
            img_bytes = img_path.read_bytes()
            res = process_image_for_monk_tone(img_bytes, crop_center_oval=True)
        except Exception as e:
            errors += 1
            per_mst[mst_gt]["failed"] += 1
            all_results.append({"file": fname, "gt": mst_gt, "pred": None, "status": f"ERROR:{e}", "lighting": light})
            continue

        if res["status"] != "OK":
            no_face += 1
            per_mst[mst_gt]["failed"] += 1
            all_results.append({"file": fname, "gt": mst_gt, "pred": None, "status": res["status"], "lighting": light})
            if idx % 25 == 0:
                print(f"  [{idx:>4}/{total}] skipped (no face/recapture)")
            continue

        pred = res["tone"]
        diff = abs(pred - mst_gt)
        is_exact   = diff == 0
        is_within1 = diff <= 1
        is_within2 = diff <= 2

        if is_exact:   exact   += 1
        if is_within1: within1 += 1
        if is_within2: within2 += 1

        if is_exact:   per_mst[mst_gt]["exact"]   += 1
        if is_within1: per_mst[mst_gt]["within1"] += 1
        if is_within2: per_mst[mst_gt]["within2"] += 1
        if is_exact:   per_lighting[light]["exact"]   += 1
        if is_within1: per_lighting[light]["within1"] += 1
        if is_within2: per_lighting[light]["within2"] += 1

        all_results.append({
            "file": fname, "gt": mst_gt, "pred": pred, "diff": diff,
            "undertone": res.get("undertone"), "confidence": res.get("confidence"),
            "lighting": light, "status": "OK"
        })

        if idx % 25 == 0 or idx == total:
            answered = idx - no_face - errors
            print(f"  [{idx:>4}/{total}] answered: {answered} | exact: {exact} | ±1: {within1} | no-face: {no_face}")

    answered = total - no_face - errors
    return {
        "label": label,
        "total": total,
        "answered": answered,
        "no_face": no_face,
        "errors": errors,
        "exact": exact,
        "within1": within1,
        "within2": within2,
        "per_mst": per_mst,
        "per_lighting": per_lighting,
        "results": all_results,
    }


def print_report(r: dict):
    total     = r["total"]
    answered  = r["answered"]
    exact     = r["exact"]
    within1   = r["within1"]
    within2   = r["within2"]
    no_face   = r["no_face"]
    pct = lambda n, d: f"{100*n/max(1,d):.1f}%"

    print(f"\n{'='*72}")
    print(f"  RESULTS: {r['label']}")
    print(f"{'='*72}")
    print(f"  Total images tested      : {total}")
    print(f"  Face detected & answered : {answered}  ({pct(answered, total)} detection rate)")
    print(f"  Recapture / no-face      : {no_face}")
    print(f"  File errors              : {r['errors']}")
    print()
    print(f"  ┌─────────────────────────────────────────────────────┐")
    print(f"  │  ACCURACY (over answered images)                    │")
    print(f"  │  Exact match (Monk ± 0):  {exact:>4} / {answered:<4}  = {pct(exact,answered):>6}  │")
    print(f"  │  Within ± 1 shade:        {within1:>4} / {answered:<4}  = {pct(within1,answered):>6}  │")
    print(f"  │  Within ± 2 shades:       {within2:>4} / {answered:<4}  = {pct(within2,answered):>6}  │")
    print(f"  └─────────────────────────────────────────────────────┘")

    print(f"\n  Accuracy per Monk Skin Tone level:")
    print(f"  {'MST':>5}  {'Images':>7}  {'Exact':>7}  {'±1 shade':>9}  {'±2 shades':>10}  {'Failed/NF':>10}")
    print(f"  {'-'*60}")
    for t in range(1, 11):
        pm = r["per_mst"][t]
        ans = pm["total"] - pm["failed"]
        print(
            f"  Monk {t:02d}  {pm['total']:>7}  {pct(pm['exact'],ans):>7}  "
            f"{pct(pm['within1'],ans):>9}  {pct(pm['within2'],ans):>10}  {pm['failed']:>10}"
        )

    print(f"\n  Accuracy per lighting condition:")
    print(f"  {'Condition':>15}  {'Images':>7}  {'Exact':>7}  {'±1 shade':>9}  {'±2 shades':>10}")
    print(f"  {'-'*55}")
    for light, lm in sorted(r["per_lighting"].items()):
        ans = lm["total"]
        print(
            f"  {light:>15}  {lm['total']:>7}  {pct(lm['exact'],ans):>7}  "
            f"{pct(lm['within1'],ans):>9}  {pct(lm['within2'],ans):>10}"
        )


if __name__ == "__main__":
    start = time.time()

    print("\n" + "="*72)
    print("  AAINA — Google MST-E OFFICIAL BENCHMARK EVALUATION")
    print("  Dataset: Monk Skin Tone Examples (MST-E), annotated by Dr. Monk")
    print("  Model:   AAINA backend/monk_service.py (pure-Python, PIL only)")
    print("="*72)

    # --- Run 1: Balanced frontal sample across all 10 MST tones
    balanced = load_dataset(max_per_mst=20)
    res_balanced = evaluate(balanced, "Balanced Frontal Sample (up to 20 per tone, well-lit priority)")
    print_report(res_balanced)

    # --- Run 2: Golden images only (Dr. Monk's hand-picked best-condition images, 1 per subject)
    golden_map  = load_golden_set()
    golden_rows = []
    all_rows = []
    with open(DETAILS_CSV, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            all_rows.append({k.strip(): v.strip() for k, v in r.items()})
    for row in all_rows:
        fname = row["image_ID"].strip()
        if fname in golden_map and golden_map[fname]["type"] == "golden" and fname.lower().endswith(".jpg"):
            golden_rows.append(row)
    res_golden = evaluate(golden_rows, "Golden Image Set (1 ideal image per subject, hand-picked by Dr. Monk)")
    print_report(res_golden)

    # --- Run 3: Adversarial images only (challenging conditions)
    adv_rows = []
    for row in all_rows:
        fname = row["image_ID"].strip()
        if fname in golden_map and golden_map[fname]["type"] == "adversarial" and fname.lower().endswith(".jpg"):
            adv_rows.append(row)
    res_adv = evaluate(adv_rows, "Adversarial Image Set (not-ideal: glare, shadow, angle, low-light)")
    print_report(res_adv)

    elapsed = time.time() - start
    print(f"\n{'='*72}")
    print(f"  Total evaluation time: {elapsed:.1f}s  |  "
          f"Images processed: {res_balanced['total'] + res_golden['total'] + res_adv['total']}")
    print("="*72 + "\n")
