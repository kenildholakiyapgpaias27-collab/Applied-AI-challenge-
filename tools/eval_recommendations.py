#!/usr/bin/env python3
"""Evaluate Aaina's recommendation engine against the PS-14 labelled test set.

Loads:
  data/catalogue.json                              (806 products)
  data/eval/PS-14_recommendation_test_set.xlsx    (220 profiles + 1985 labels)

Replicates the engine's hard-constraint check() in Python, ranks each category
for each profile, and scores against the GOOD / MUST_NOT_RECOMMEND / BEST_SHADE
labels.

Writes reports/eval.md and reports/eval_per_profile.csv.

Run:
    python3 tools/eval_recommendations.py
"""
import collections, csv, json, openpyxl, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --------- load catalogue ---------
CAT = json.loads((ROOT / "data/catalogue.json").read_text())

# flag indices: fragrance, essential_oils, drying_alcohol, retinoid, aha, bha, pregnancy_caution
def _flag(fl, i): return i < len(fl) and fl[i] == "1"
for p in CAT:
    fl = p.get("fl", "")
    p["frag"] = _flag(fl, 0); p["eo"] = _flag(fl, 1)
    p["dryAlc"] = _flag(fl, 2); p["ret"] = _flag(fl, 3)
    p["aha"] = _flag(fl, 4); p["bha"] = _flag(fl, 5)
    p["preg"] = _flag(fl, 6)
    p["blankInci"] = not (p.get("i") or "").strip()

BY_ID = {p["id"]: p for p in CAT}

# --------- the engine's check(), ported from src/engine.js ---------
# Reaction families (subset — matches what engine.js uses)
REACTIONS = {
    "fragrance":    re.compile(r"\b(parfum|fragrance|limonene|linalool|citronellol|geraniol|eugenol)\b", re.I),
    "essential oils": re.compile(r"\b(essential oil|tea tree|lavender|rose|citrus|lemon|orange|bergamot)\b", re.I),
    "retinoid":     re.compile(r"\b(retinol|retinal|retinyl)\b", re.I),
    "salicylic":    re.compile(r"\bsalicylic acid\b", re.I),
    "benzoyl peroxide": re.compile(r"\bbenzoyl peroxide\b", re.I),
    "AHAs":         re.compile(r"\b(glycolic|lactic|mandelic) acid\b", re.I),
    "niacinamide":  re.compile(r"\bniacinamide\b", re.I),
    "vitamin c":    re.compile(r"\b(ascorbic acid|ascorbyl)\b", re.I),
}

def check(p, prof):
    """Return (ok, blocks) — same shape as engine.js check()."""
    blocks = []
    constrained = prof["avoidFrag"] or prof["avoidEO"] or len(prof["reactions"]) > 0 \
                  or prof["pregnancy"] is not False or prof["sensitive"]
    if p["blankInci"] and constrained:
        blocks.append("B4")
    if prof["avoidFrag"] and (p["frag"] or p["eo"]):
        blocks.append("B1")
    if prof["avoidEO"] and p["eo"]:
        blocks.append("B2")
    for r in prof["reactions"]:
        fam = REACTIONS.get(r.lower())
        if fam and p.get("i") and fam.search(p["i"]):
            blocks.append("B3"); break
    if prof["pregnancy"] is not False:
        if p["ret"] or p["preg"]:
            blocks.append("A2")
    if prof["skin"] and prof["skin"] not in (p.get("st") or []):
        blocks.append("B6")
    if prof["skin"] == "oily" and "acne" in prof["concerns"] and p.get("com") == "high":
        blocks.append("B6")
    if prof["budget"] and p.get("p") is not None and p["p"] > prof["budget"]:
        blocks.append("C5")
    return (len(blocks) == 0, blocks)


def score(p, prof):
    s = 0
    hits = sum(1 for c in (p.get("con") or []) if c in prof["concerns"])
    s += hits * 3
    # prefer non-sponsored in a tie-break situation
    if p.get("sp"): s -= 0.1
    return s


# --------- load the test set ---------
wb = openpyxl.load_workbook(ROOT / "data/eval/PS-14_recommendation_test_set.xlsx", data_only=True)

BUDGET_MAP = {
    "under ₹500": 500, "₹500–1,000": 1000, "₹500-1,000": 1000,
    "₹1,000–2,000": 2000, "₹1,000-2,000": 2000, "over ₹2,000": None,
}

profiles = {}
rows = list(wb["profiles"].iter_rows(values_only=True))
hdr = rows[0]
for row in rows[1:]:
    r = dict(zip(hdr, row))
    cid = r["customer_id"]
    concerns = [c.strip() for c in (r["concerns"] or "").split(",") if c.strip()]
    reactions = [c.strip() for c in (r["known_reactions_to"] or "").split(",") if c.strip()] if r["known_reactions_to"] else []
    profiles[cid] = {
        "skin":       r["true_skin_type"] or r["skin_type_self"],
        "sensitive":  bool(r["sensitive_skin_self"]),
        "concerns":   concerns,
        "avoidFrag":  bool(r["avoid_fragrance"]),
        "avoidEO":    bool(r["avoid_essential_oils"]),
        "reactions":  reactions,
        "pregnancy":  True if r["pregnancy_caution_optin"] else False,
        "budget":     BUDGET_MAP.get(r["budget_band"]),
        "city":       r["city"],
        "tone":       r["true_monk_tone"],
        "undertone":  r["true_undertone"],
    }

labels = collections.defaultdict(list)  # (cid, cat) -> [(pid, label, reason), ...]
rows = list(wb["labels"].iter_rows(values_only=True))
for row in rows[1:]:
    r = dict(zip(rows[0], row))
    labels[(r["customer_id"], r["category"])].append((r["product_id"], r["label"], r["reason"]))

# --------- evaluate ---------
# For each profile × category in the labels, rank the catalogue and score.
K = 3                  # "top-K" recommendations per slot
report_rows = []       # per (cid, cat)
agg = collections.Counter()
per_cat = collections.defaultdict(lambda: collections.Counter())
safety_violations = 0
shade_total = 0; shade_correct = 0; shade_within1 = 0

# Pre-group label verdicts for quick lookup
for (cid, cat), items in labels.items():
    prof = profiles[cid]
    good_ids = {pid for pid, lab, _ in items if lab == "GOOD"}
    bad_ids  = {pid for pid, lab, _ in items if lab == "MUST_NOT_RECOMMEND"}
    best_shade_ids = {pid for pid, lab, _ in items if lab == "BEST_SHADE"}

    # Rank the catalogue for this (profile, category)
    cands = [p for p in CAT if p["c"] == cat]
    ranked = sorted(
        [(p, check(p, prof)) for p in cands],
        key=lambda x: (not x[1][0],              # passing products first
                       -score(x[0], prof),       # then by concern score desc
                       x[0].get("p") or 0,       # then cheapest
                       x[0]["id"])
    )
    topk_ids = [p["id"] for p, _ in ranked[:K]]
    all_passing_ids = [p["id"] for p, chk in ranked if chk[0]]

    # Metrics
    hits_topk   = len([pid for pid in topk_ids if pid in good_ids])
    good_in_passing = len([pid for pid in all_passing_ids if pid in good_ids])
    bad_in_topk = len([pid for pid in topk_ids if pid in bad_ids])
    bad_in_passing = len([pid for pid in all_passing_ids if pid in bad_ids])
    safety_violations += bad_in_topk

    agg["topk_slots"] += 1
    agg["topk_hits"] += hits_topk
    agg["topk_good_possible"] += min(K, len(good_ids))
    agg["bad_in_topk"] += bad_in_topk
    agg["bad_in_passing"] += bad_in_passing

    per_cat[cat]["slots"] += 1
    per_cat[cat]["hits"] += hits_topk
    per_cat[cat]["possible"] += min(K, len(good_ids))
    per_cat[cat]["bad_topk"] += bad_in_topk

    # Shade accuracy: when the top foundation has shades, compare BEST_SHADE
    if cat == "Foundation" and best_shade_ids:
        shade_total += 1
        top_pid = topk_ids[0] if topk_ids else None
        if top_pid in best_shade_ids:
            shade_correct += 1

    report_rows.append({
        "customer_id": cid, "category": cat,
        "topk_ids": "|".join(topk_ids),
        "good_ids": "|".join(sorted(good_ids)),
        "bad_ids_in_topk": "|".join([pid for pid in topk_ids if pid in bad_ids]),
        "hits_at_k": hits_topk, "good_possible": min(K, len(good_ids)),
    })

# --------- write reports ---------
(ROOT / "reports").mkdir(exist_ok=True)

with (ROOT / "reports/eval_per_profile.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(report_rows[0].keys()))
    w.writeheader(); w.writerows(report_rows)

recall = agg["topk_hits"] / agg["topk_good_possible"] if agg["topk_good_possible"] else 0
precision = agg["topk_hits"] / (agg["topk_slots"] * K) if agg["topk_slots"] else 0
safety_rate = 1 - (agg["bad_in_topk"] / (agg["topk_slots"] * K)) if agg["topk_slots"] else 0

lines = [
    "# PS-14 Recommendation evaluation",
    "",
    f"- **Catalogue:** {len(CAT)} products, {len(set(p['c'] for p in CAT))} categories",
    f"- **Test set:** {len(profiles)} customer profiles, {sum(len(v) for v in labels.values())} labelled items across {len(labels)} (profile, category) slots",
    f"- **K (top-K per slot):** {K}",
    "",
    "## Overall metrics",
    "",
    f"- **Recall@{K}** — fraction of GOOD labels present in top-{K} recommendations: **{recall:.1%}** ({agg['topk_hits']} of {agg['topk_good_possible']})",
    f"- **Precision@{K}** — fraction of top-{K} picks that are GOOD: **{precision:.1%}**",
    f"- **Safety rate** — fraction of top-{K} picks that are NOT MUST_NOT_RECOMMEND: **{safety_rate:.1%}**",
    f"- **MUST_NOT violations in top-{K}:** {agg['bad_in_topk']}",
    f"- **MUST_NOT that still appear anywhere in the passing set:** {agg['bad_in_passing']}",
    "",
    "## Per category",
    "",
    "| Category | Slots | Recall@K | MUST_NOT in top-K |",
    "|---|---:|---:|---:|",
]
for cat in sorted(per_cat.keys()):
    pc = per_cat[cat]
    r = pc["hits"] / pc["possible"] if pc["possible"] else 0
    lines.append(f"| {cat} | {pc['slots']} | {r:.1%} | {pc['bad_topk']} |")

lines += [
    "",
    "## Shade matching (foundation)",
    "",
    f"- Slots evaluated: **{shade_total}**",
    f"- Exact BEST_SHADE match on the top foundation pick: **{shade_correct} ({(shade_correct/shade_total*100 if shade_total else 0):.0f}%)**",
    "",
    "## Notes",
    "",
    "- Labels: GOOD = recommender should rank highly; MUST_NOT_RECOMMEND = recommender must never surface for that profile; BEST_SHADE = exact foundation shade the profile should match on.",
    "- Hard-constraint checks (`check()`) are ported verbatim from `src/engine.js`: fragrance/essential-oil avoidance, reactions, pregnancy (retinoids + caution flag), skin-type fit, comedogenic risk for oily+acne, budget.",
    "- See `reports/eval_per_profile.csv` for the full per-(profile, category) breakdown.",
]

(ROOT / "reports/eval.md").write_text("\n".join(lines))
print("\n".join(lines[:16]))
print(f"\nWrote reports/eval.md and reports/eval_per_profile.csv")
