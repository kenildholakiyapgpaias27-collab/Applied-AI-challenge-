#!/usr/bin/env python3
"""Validate data/evidence/actives_timeline.json and print evidence coverage for the catalogue.

    python3 tools/check_evidence.py            # exit 1 on any problem

Checks: schema, every checkpoint cites a known reference, no checkpoint lies past the length of the study it
cites, numbers are ordered (low <= typical <= high) and only appear with a numeric kind, grade-D entries have no
timeline, and every user-facing sentence passes the wording rules (no promises, no medical terms).
Then shows which catalogue products have grade A / B / C / D evidence (same matching as src/timeline.js).
"""
import collections, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = json.loads((ROOT / "data/evidence/actives_timeline.json").read_text(encoding="utf-8"))
CAT = json.loads((ROOT / "data/catalogue.json").read_text(encoding="utf-8"))
KINDS = {"qualitative", "change", "responders", "ratio", "protective"}
GRADES = "ABCD"
# wording rules from the safety guide and Indian advertising rules (kept in step with BANNED in src/timeline.js)
BANNED = re.compile(r"\b(you will|guarantee\w*|cures?|cured|curing|removes?|removal|lighten\w*|brighten\w*|whiten\w*|fairer|fairness|"
                    r"treat(s|ed|ment|ing)?|heal\w*|eliminat\w*|permanent\w*|melasma|rosacea|eczema|psoriasis|dermatitis|acne|hyperpigmentation|PIH)\b", re.I)
SKINCARE = {"Serum", "Moisturiser", "Sunscreen", "Cleanser", "Toner", "Exfoliant", "Face mask", "Eye cream", "Spot treatment", "Lip care", "Face oil"}
problems = []
def bad(m): problems.append(m)

def text_fields(e):
    yield e.get("note"); yield e.get("beyond_last_study"); yield e.get("concern")
    for c in e["checkpoints"]: yield c["plain"]

for e in EV["entries"]:
    eid = e.get("id", "?")
    for k in ("id", "active", "match", "concern", "app_concerns", "evidence_strength", "checkpoints", "refs"):
        if k not in e: bad(f"{eid}: missing {k}")
    g = e.get("evidence_strength")
    if g not in GRADES: bad(f"{eid}: grade {g!r}")
    if g == "D":
        if e["checkpoints"]: bad(f"{eid}: grade D must not have a timeline")
        continue
    if not e["checkpoints"]: bad(f"{eid}: no checkpoints but grade {g}")
    if not e.get("population"): bad(f"{eid}: population missing")
    elif "deeper_tones" not in e["population"]: bad(f"{eid}: say what is known for deeper skin tones")
    for c in e["checkpoints"]:
        r = EV["refs"].get(c.get("ref"))
        if not r: bad(f"{eid}: checkpoint at {c.get('weeks')}w has no known reference"); continue
        if c["ref"] not in e["refs"]: bad(f"{eid}: {c['ref']} not listed in the entry's refs")
        if c["weeks"] > r["study_weeks"] + 1e-9: bad(f"{eid}: checkpoint at {c['weeks']}w is past the end of study {c['ref']} ({r['study_weeks']}w)")
        if c["kind"] not in KINDS: bad(f"{eid}: kind {c['kind']!r}")
        if c.get("grade") not in GRADES[:3]: bad(f"{eid}: checkpoint grade {c.get('grade')!r}")
        if GRADES.index(c["grade"]) < GRADES.index(g): bad(f"{eid}: a checkpoint can't be graded above its entry")
        nums = [c[k] for k in ("change_low", "change_typical", "change_high")]
        if c["kind"] == "qualitative" and any(v is not None for v in nums): bad(f"{eid}: qualitative checkpoint with numbers")
        if c["kind"] != "qualitative":
            if all(v is None for v in nums): bad(f"{eid}: {c['kind']} checkpoint without a number")
            if not c.get("unit"): bad(f"{eid}: number without a unit")
        lo, ty, hi = nums
        if lo is not None and ty is not None and lo > ty: bad(f"{eid}: change_low > change_typical")
        if ty is not None and hi is not None and ty > hi: bad(f"{eid}: change_typical > change_high")
        if lo is not None and hi is not None and lo > hi: bad(f"{eid}: change_low > change_high")
    for t in text_fields(e):
        if t and BANNED.search(t): bad(f"{eid}: banned wording {BANNED.search(t).group(0)!r} in: {t[:80]}")
for k, r in EV["refs"].items():
    for f in ("pmid", "title", "year", "journal", "funder", "design", "study_weeks"):
        if r.get(f) in (None, ""): bad(f"ref {k}: missing {f}")

# ---- coverage: the same matching as src/timeline.js (key actives, or the Sunscreen category) ----
RINSE_OFF = {"Cleanser", "Face mask"}   # studies tested leave-on products; a wash-off product gets no timeline
def matches(p, e):
    if p["c"] in RINSE_OFF: return False
    hay = (p.get("a") or "").lower()
    if p["c"] == "Sunscreen" and e["active"] == "Sunscreen": return True
    return e["active"] != "Sunscreen" and any(m in hay for m in e["match"])
def best_grade(p):
    gs = [e["evidence_strength"] for e in EV["entries"] if matches(p, e)]
    return min(gs, key=GRADES.index) if gs else "D"
rows = collections.defaultdict(collections.Counter); no_tl = collections.Counter()
for p in CAT:
    if p["c"] not in SKINCARE: continue
    g = best_grade(p); rows[p["c"]][g] += 1
    if g == "D": no_tl["rinse-off product (studies were leave-on)" if p["c"] in RINSE_OFF else "no key actives listed" if not p.get("a") else "only actives without suitable evidence"] += 1
tot = collections.Counter()
print(f"{'Category':16s}  A    B    C    D   total")
for c in sorted(rows):
    r = rows[c]; tot.update(r)
    print(f"{c:16s} {r['A']:3d}  {r['B']:3d}  {r['C']:3d}  {r['D']:3d}   {sum(r.values()):4d}")
print(f"{'All skincare':16s} {tot['A']:3d}  {tot['B']:3d}  {tot['C']:3d}  {tot['D']:3d}   {sum(tot.values()):4d}")
print("No timeline (grade D):", dict(no_tl))
print("Evidence grade by active:", ", ".join(f"{e['active']} ({e['concern_key']}) {e['evidence_strength']}" for e in EV["entries"]))
if problems:
    print("\nPROBLEMS:"); [print(" -", m) for m in problems]; sys.exit(1)
print(f"\nOK: {len(EV['entries'])} entries, {sum(len(e['checkpoints']) for e in EV['entries'])} checkpoints, {len(EV['refs'])} references, all checks passed")
