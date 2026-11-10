"""Catalogue data-quality check (run on every catalogue update).

Finds tags that contradict each other, because the guardrails trust the catalogue: a wrong
skin-type tag silently removes good products (or lets a wrong one through).

  --fix    applies the safe, rule-based corrections below and writes catalogue.json
           (a backup is kept); anything ambiguous is only reported, for a human to review.
"""
import json, sys, pathlib, shutil, re, collections
ROOT = pathlib.Path(__file__).resolve().parent.parent
CAT_PATH = ROOT / "data" / "catalogue.json"
cat = json.load(open(CAT_PATH))
SKINCARE = {"Cleanser", "Serum", "Spot treatment", "Sunscreen", "Moisturiser", "Exfoliant", "Toner", "Eye cream", "Face mask", "Face oil"}
FL = ["fragrance", "essential oil", "drying alcohol", "retinoid", "AHA", "BHA", "pregnancy caution"]
RX = {0: r"\b(parfum|fragrance|limonene|linalool|geraniol|citronellol|citral|eugenol|coumarin)\b", 3: r"\b(retinol|retinal|retinyl|retinoate|adapalene)\b",
      4: r"\b(glycolic|lactic|mandelic) acid\b", 5: r"\bsalicylic acid\b"}
fixes, review = [], []
for p in cat:
    if p["c"] not in SKINCARE: continue
    st, con, inci, act = set(p["st"]), set(p["con"]), (p.get("i") or "").lower(), (p.get("a") or "").lower()
    # R1: a product made for acne or oil control must suit oily skin (who else has those concerns?)
    if (con & {"acne", "oiliness"}) and "oily" not in st and p["c"] != "Face oil":
        fixes.append((p["id"], p["n"], "skin types", "acne / oil-control product not tagged for oily skin", "add 'oily'")); p["st"] = p["st"] + ["oily"]
    # R2: a product made for dryness must suit dry skin, except exfoliants (can be too harsh: human review)
    if "dehydration" in con and "dry" not in st:
        if p["c"] == "Exfoliant": review.append((p["id"], p["n"], "skin types", "hydration claim but not for dry skin (exfoliant: may be intentional)", "review"))
        else: fixes.append((p["id"], p["n"], "skin types", "hydration product not tagged for dry skin", "add 'dry'")); p["st"] = p["st"] + ["dry"]
    # R3: flags that disagree with the ingredient list (the engine already uses the stricter of the two; reported so the data gets corrected at source)
    for k, rx in RX.items():
        has = bool(re.search(rx, inci + " " + act)); flag = p["fl"][k] == "1"
        if p.get("i") and has != flag: review.append((p["id"], p["n"], "flag", f"{FL[k]} flag says {'yes' if flag else 'no'} but the ingredient list says {'yes' if has else 'no'}", "fix flag at source"))
    # R4: missing ingredient list
    if not p.get("i"): review.append((p["id"], p["n"], "ingredients", "ingredient list missing (blocked for anyone with a safety constraint)", "get INCI from the brand"))
    # R5: sunscreen without SPF
    if p["c"] == "Sunscreen" and not p.get("spf"): review.append((p["id"], p["n"], "SPF", "sunscreen has no SPF value", "add SPF"))
print(f"Auto-fixed: {len(fixes)}   For review: {len(review)}")
for f in fixes: print("  FIX   ", *f, sep=" | ")
c = collections.Counter(r[2] for r in review); print("  review by type:", dict(c))
json.dump({"fixes": fixes, "review": review}, open(ROOT / "tools" / "catalogue_check.json", "w"), indent=1, ensure_ascii=False)
if "--fix" in sys.argv and fixes:
    shutil.copy(CAT_PATH, ROOT / "data" / "catalogue.pre-datafix.json")
    json.dump(cat, open(CAT_PATH, "w"), ensure_ascii=False, separators=(",", ":"))
    print("catalogue.json updated (backup: catalogue.pre-datafix.json)")
