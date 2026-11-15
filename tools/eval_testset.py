#!/usr/bin/env python3
"""Evaluate the advisor and the try-on on the PS-14 labelled test set.

    python3 tools/eval_testset.py [--visual] [--month N]

Reads data/eval/PS-14_recommendation_test_set.xlsx, runs the REAL engine (src/engine.js, through
tools/eval_engine.js in Node) on the self-reported answers only, then scores:
  A. try-on shade accuracy ("Your match") by tone band, vs a naive baseline and vs the engine's
     unused tone correction
  B. safety: MUST_NOT products in the top 5, and check() recall on every MUST_NOT label
  C. relevance: GOOD hit rate in the top 5, overall and per category
Writes reports/eval_testset.json and reports/eval_testset.md. --visual also renders
reports/tryon_visual_check.png in Chrome (needs playwright, Pillow, Chrome).

Ground truth (true_skin_type, true_monk_tone, true_undertone) is used ONLY for scoring: inputs
are built from a whitelist of self-reported columns, and any read of a true_* field while
building inputs stops the run.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "data/eval/PS-14_recommendation_test_set.xlsx"
REPORTS = ROOT / "reports"
SELF = ["customer_id", "city", "climate", "age_band", "skin_type_self", "sensitive_skin_self", "concerns", "avoid_fragrance",
        "avoid_essential_oils", "known_reactions_to", "pregnancy_caution_optin", "budget_band", "monk_tone_self", "undertone_self"]
TRUTH = ["true_skin_type", "true_monk_tone", "true_undertone"]
BANDS = [("1–3", 1, 3), ("4–7", 4, 7), ("8–10", 8, 10)]


class InputRow(dict):
    """a profile row that refuses to hand out ground truth"""
    def __getitem__(self, k):
        if str(k).startswith("true_"):
            raise RuntimeError(f"ground truth column {k} read while building inputs")
        return super().__getitem__(k)
    get = lambda self, k, d=None: self[k] if k in self else d


def load():
    wb = openpyxl.load_workbook(XLSX, read_only=True)
    rows = list(wb["profiles"].iter_rows(values_only=True))
    head = rows[0]
    full = [dict(zip(head, r)) for r in rows[1:]]
    inputs = [{k: InputRow(r)[k] for k in SELF} for r in full]       # whitelist: self-reported only
    truth = {r["customer_id"]: {k: r[k] for k in TRUTH} for r in full}
    lab = list(wb["labels"].iter_rows(values_only=True))
    labels = [dict(zip(lab[0], r)) for r in lab[1:]]
    for i in inputs:
        assert not any(k.startswith("true_") for k in i), "truth leaked into inputs"
    return inputs, truth, labels


def run_engine(inputs, categories, month, src_root=None):
    node = shutil.which("node")
    if not node:
        sys.exit("node is required (the engine runs in Node)")
    tmp = Path(tempfile.mkdtemp(prefix="aaina_eval_"))
    (tmp / "in.json").write_text(json.dumps({"profiles": inputs, "categories": categories}, ensure_ascii=False))
    args = [node, str(ROOT / "tools/eval_engine.js"), str(tmp / "in.json"), str(tmp / "out.json")] + ([str(month)] if month is not None else [])
    env = dict(__import__("os").environ, **({"AAINA_EVAL_ROOT": str(src_root)} if src_root else {}))
    r = subprocess.run(args, capture_output=True, text=True, env=env)
    print(r.stdout.strip())
    if r.returncode:
        sys.exit(f"engine run failed: {r.stderr}")
    return json.loads((tmp / "out.json").read_text())


def pct(n, d):
    return round(100 * n / d, 1) if d else None


def band_of(t):
    return next(b for b, lo, hi in BANDS if lo <= t <= hi)


def naive_baseline(shades, tone, ut):
    """the shade whose depth equals the self-reported tone with the self-reported undertone (nearest if none)"""
    ut = None if str(ut).lower().startswith("don") else ut
    best, bs = 0, None
    for i, s in enumerate(shades):
        sc = abs(s[1] - tone) * 10 + (0 if ut is None or s[2] == ut else 1)
        if bs is None or sc < bs:
            best, bs = i, sc
    return best


def shade_metrics(rows):
    n = len(rows)
    if not n:
        return {"n": 0}
    err = [r["pred_depth"] - r["true_tone"] for r in rows]
    return {"n": n, "exact_hit": pct(sum(r["exact"] for r in rows), n),
            "depth_err_mean": round(sum(err) / n, 2), "depth_mae": round(sum(abs(e) for e in err) / n, 2),
            "within_1": pct(sum(abs(e) <= 1 for e in err), n), "off_by_2plus": pct(sum(abs(e) >= 2 for e in err), n),
            "undertone_match": pct(sum(r["pred_und"] == r["true_und"] for r in rows), n),
            "within_1_of_best": pct(sum(abs(r["pred_depth"] - r["best_depth"]) <= 1 for r in rows), n)}


def score(inputs, truth, labels, eng, cat):
    by_cust = {p["customer_id"]: p for p in eng["profiles"]}
    inp = {i["customer_id"]: i for i in inputs}
    res = {}

    # ---------- A. shade accuracy ----------
    variants = {"tryon": [], "baseline": [], "labelled_best": []}
    worst = []
    for l in labels:
        if l["label"] != "BEST_SHADE":
            continue
        cid, pid = l["customer_id"], l["product_id"]
        m = re.match(r"(P\d+)-S(\d+)", l["reason"])
        best_i = int(m.group(2)) - 1
        shades = cat[pid]["s"]
        t = truth[cid]
        e = by_cust[cid]["match"][pid]
        picks = {"tryon": e["tryon"],
                 "baseline": naive_baseline(shades, inp[cid]["monk_tone_self"], inp[cid]["undertone_self"])}
        picks["labelled_best"] = best_i
        for v, i in picks.items():
            variants.setdefault(v, [])
            s = shades[i]
            variants[v].append({"cid": cid, "pid": pid, "pred": i, "best": best_i, "exact": i == best_i, "pred_depth": s[1], "pred_und": s[2],
                                "best_depth": shades[best_i][1],
                                "true_tone": t["true_monk_tone"], "true_und": t["true_undertone"], "band": band_of(t["true_monk_tone"])})
        r = variants["tryon"][-1]
        assert r["cid"] == cid
        worst.append({"customer_id": cid, "product": pid, "self_tone": inp[cid]["monk_tone_self"], "self_undertone": inp[cid]["undertone_self"],
                      "true_tone": t["true_monk_tone"], "true_undertone": t["true_undertone"],
                      "predicted": f"{pid}-S{r['pred']+1:02d} {shades[r['pred']][0]} (depth {shades[r['pred']][1]}, {shades[r['pred']][2]})",
                      "best": f"{pid}-S{best_i+1:02d} {shades[best_i][0]} (depth {shades[best_i][1]}, {shades[best_i][2]})",
                      "depth_error": shades[r["pred"]][1] - t["true_monk_tone"], "exact": r["exact"],
                      "pred_hex": shades[r["pred"]][3], "best_hex": shades[best_i][3], "pred_i": r["pred"], "best_i": best_i})
    A = {}
    for v, rows in variants.items():
        A[v] = {"overall": shade_metrics(rows), "bands": {b: shade_metrics([r for r in rows if r["band"] == b]) for b, _, _ in BANDS}}
        for k in ("exact_hit", "within_1", "undertone_match", "within_1_of_best"):
            vals = [A[v]["bands"][b][k] for b, _, _ in BANDS if A[v]["bands"][b]["n"]]
            A[v].setdefault("band_gap", {})[k] = round(max(vals) - min(vals), 1)
    worst.sort(key=lambda w: (-abs(w["depth_error"]), w["exact"], w["customer_id"]))
    A["worst_misses"] = worst[:10]
    res["A"] = A

    # ---------- B. safety ----------
    must = [l for l in labels if l["label"] == "MUST_NOT_RECOMMEND"]
    must_by = defaultdict(set)
    for l in must:
        must_by[l["customer_id"]].add(l["product_id"])
    flagged = [cid for cid, ids in must_by.items() if ids & {pid for v in by_cust[cid]["top5"].values() for pid in v}]
    org_st = {}
    org = ROOT / "data/eval/PS-14_catalogue.xlsx"
    if org.exists():
        rows = list(openpyxl.load_workbook(org, read_only=True)["products"].iter_rows(values_only=True))
        h = rows[0]
        for r in rows[1:]:
            d = dict(zip(h, r))
            org_st[d["product_id"]] = {x.strip() for x in str(d["skin_types_suited"] or "").split(",") if x.strip()}
    leaks = []
    for l in must:
        e = by_cust[l["customer_id"]]
        if l["product_id"] in set(e["passing"]):
            t = truth[l["customer_id"]]
            needs_truth = bool(re.match(r"not suited to (\w+) skin", l["reason"])) and t["true_skin_type"] != inp[l["customer_id"]]["skin_type_self"]
            leaks.append({"customer_id": l["customer_id"], "category": l["category"], "product_id": l["product_id"], "reason": l["reason"],
                          "self_skin": inp[l["customer_id"]]["skin_type_self"], "true_skin": t["true_skin_type"],
                          "cause": "label uses the measured skin type; the customer told the quiz a different one" if needs_truth
                          else (f"our catalogue tags it for {inp[l['customer_id']]['skin_type_self']} skin; the organisers' catalogue doesn't "
                                "(added by tools/catalogue_check.py --fix)") if org_st.get(l["product_id"]) is not None
                          and inp[l["customer_id"]]["skin_type_self"] in cat[l["product_id"]]["st"]
                          and inp[l["customer_id"]]["skin_type_self"] not in org_st[l["product_id"]] else "engine gap"})
    def knowable_label(l):
        m = re.search(r"not suited to (\w+) skin", l["reason"])
        return not (m and inp[l["customer_id"]]["skin_type_self"] != truth[l["customer_id"]]["true_skin_type"])
    elig = [l for l in must if knowable_label(l)]
    leak_keys = {(x["customer_id"], x["product_id"]) for x in leaks}
    knowable = {"labels": len(elig), "blocked": sum((l["customer_id"], l["product_id"]) not in leak_keys for l in elig),
                "recall": pct(sum((l["customer_id"], l["product_id"]) not in leak_keys for l in elig), len(elig))}
    flagged_detail = [{"customer_id": cid, "category": c, "product_id": pid, "reason": next(l["reason"] for l in must if l["customer_id"] == cid and l["product_id"] == pid),
                       "self_skin": inp[cid]["skin_type_self"], "true_skin": truth[cid]["true_skin_type"]}
                      for cid in flagged for c, ids in by_cust[cid]["top5"].items() for pid in ids if pid in must_by[cid]]
    by_reason = Counter(re.sub(r"contains .* — known reaction", "contains <ingredient> — known reaction", l["reason"]) for l in must)
    leak_reason = Counter(re.sub(r"contains .* — known reaction", "contains <ingredient> — known reaction", l["reason"]) for l in leaks)
    res["B"] = {"profiles_with_must_not_in_top5": pct(len(flagged), len(inputs)), "profiles_flagged": sorted(flagged), "flagged_detail": flagged_detail,
                "must_not_total": len(must), "blocked_by_check": len(must) - len(leaks), "recall": pct(len(must) - len(leaks), len(must)),
                "recall_on_knowable_labels": knowable,
                "by_reason": {k: {"labels": v, "leaked": leak_reason.get(k, 0)} for k, v in by_reason.most_common()},
                "leaks": leaks,
                "tryon_note": "MUST_NOT labels cover skincare only; the try-on shows makeup. Its 'Not suitable for you' uses the same check(), "
                              "and 'Add look to my plan' only adds products that pass check()."}

    # ---------- C. relevance ----------
    good = defaultdict(set)
    for l in labels:
        if l["label"] == "GOOD":
            good[(l["customer_id"], l["category"])].add(l["product_id"])
    per = defaultdict(lambda: [0, 0, 0, 0])      # groups, hits, good items, good items found
    for (cid, c), ids in good.items():
        top = set(by_cust[cid]["top5"].get(c, []))
        g = per[c]
        g[0] += 1; g[1] += bool(ids & top); g[2] += len(ids); g[3] += len(ids & top)
    tot = [sum(v[i] for v in per.values()) for i in range(4)]
    res["C"] = {"overall": {"groups": tot[0], "hit_rate": pct(tot[1], tot[0]), "good_recall": pct(tot[3], tot[2])},
                "per_category": {c: {"groups": v[0], "hit_rate": pct(v[1], v[0]), "good_recall": pct(v[3], v[2])} for c, v in sorted(per.items())}}
    res["mapping_notes"] = Counter(n for p in eng["profiles"] for n in p["notes"])
    return res


def write_reports(res, month):
    REPORTS.mkdir(exist_ok=True)
    meta = {"date": date.today().isoformat(), "month_used_for_season": month, "test_set": XLSX.name}
    (REPORTS / "eval_testset.json").write_text(json.dumps({"meta": meta, **res}, indent=1, ensure_ascii=False, default=list))
    A, B, C = res["A"], res["B"], res["C"]
    L = [f"# Test-set evaluation ({meta['date']})", "",
         f"Engine: `src/engine.js` run in Node by `tools/eval_testset.py` on the 220 profiles of `{XLSX.name}` (synthetic, from the challenge organisers), "
         "using only the self-reported answers. Ground truth is used for scoring only.", "",
         *(before_after(res) if res.get("compare") else []),
         "## A. Try-on shade accuracy (\"Your match\")", "",
         ("\"Your match\" in the try-on is `bestShade(product, matchTone(), self undertone or neutral)`: the self-picked tone corrected by "
          "`matchTone()`, the same call the plan page uses. " if res.get("tryon_call") == "matchTone" else
          "\"Your match\" in the try-on is `bestShade(product, self tone, self undertone or neutral)`, the same call the plan page uses. ") +
         "Scored on each customer's BEST_SHADE foundation. Bands are by measured (true) tone.", ""]
    for v, title in (("tryon", "Try-on \"Your match\""), ("baseline", "Naive baseline: depth = self tone, same undertone"),
                     ("labelled_best", "Ceiling: the labelled best shade itself (how close the catalogue can get)")):
        L += [f"**{title}**", "", "| Band | n | Exact shade | Depth error vs true tone (mean) | MAE | Within 1 | Off by 2+ | Undertone match | Within 1 of labelled best |", "|---|---|---|---|---|---|---|---|---|"]
        for b in ["overall"] + [x for x, _, _ in BANDS]:
            m = A[v]["overall"] if b == "overall" else A[v]["bands"][b]
            if not m.get("n"):
                continue
            L.append(f"| {'All' if b == 'overall' else b} | {m['n']} | {m['exact_hit']}% | {m['depth_err_mean']:+} | {m['depth_mae']} | {m['within_1']}% | {m['off_by_2plus']}% | {m['undertone_match']}% | {m['within_1_of_best']}% |")
        g = A[v]["band_gap"]
        L += ["", f"Band gap (best minus worst): exact shade {g['exact_hit']} pts, within 1 step of true tone {g['within_1']} pts, within 1 of labelled best {g['within_1_of_best']} pts, undertone {g['undertone_match']} pts. Target: under 5 pts.", ""]
    L += ["**10 worst misses (try-on)**", "", "| Customer | Self tone / undertone | True tone / undertone | Predicted | Labelled best | Depth error |", "|---|---|---|---|---|---|"]
    for w in A["worst_misses"]:
        L.append(f"| {w['customer_id']} | {w['self_tone']} / {w['self_undertone']} | {w['true_tone']} / {w['true_undertone']} | {w['predicted']} | {w['best']} | {w['depth_error']:+} |")
    L += ["", "## B. Safety", "",
          f"- Profiles with any MUST_NOT product in the top 5 of any category: **{B['profiles_with_must_not_in_top5']}%** ({len(B['profiles_flagged'])} of 220). Target 0.",
          f"- MUST_NOT products blocked by `check()`: **{B['blocked_by_check']} of {B['must_not_total']} ({B['recall']}%)**. Target 100%.",
          f"- On labels the quiz can know (all except skin-type labels where the customer's own answer differs from the measured skin type): "
          f"**{B['recall_on_knowable_labels']['blocked']} of {B['recall_on_knowable_labels']['labels']} ({B['recall_on_knowable_labels']['recall']}%)**.",
          *[f"- In a top 5: {x['customer_id']} · {x['category']} · {x['product_id']}: {x['reason']} (told us {x['self_skin']}, measured {x['true_skin']})." for x in B["flagged_detail"]], "",
          "| MUST_NOT reason | Labels | Leaked |", "|---|---|---|"]
    for k, v in B["by_reason"].items():
        L.append(f"| {k} | {v['labels']} | {v['leaked']} |")
    if B["leaks"]:
        L += ["", "Leaks:", "", "| Customer | Category | Product | Reason | Self / true skin | Cause |", "|---|---|---|---|---|---|"]
        for x in B["leaks"]:
            L.append(f"| {x['customer_id']} | {x['category']} | {x['product_id']} | {x['reason']} | {x['self_skin']} / {x['true_skin']} | {x['cause']} |")
    L += ["", B["tryon_note"], "", "## C. Relevance", "",
          f"GOOD hit rate in the top 5 (a customer-category counts as a hit if any GOOD product is in our top 5): **{C['overall']['hit_rate']}%** "
          f"over {C['overall']['groups']} customer-categories; {C['overall']['good_recall']}% of all GOOD products appear in a top 5.", "",
          "| Category | Customer-categories | Hit rate | GOOD recall |", "|---|---|---|---|"]
    for c, v in C["per_category"].items():
        L.append(f"| {c} | {v['groups']} | {v['hit_rate']}% | {v['good_recall']}% |")
    L += ["", "## How profiles were mapped", "",
          "- Skin type, sensitive, fragrance, essential oils, pregnancy caution: straight from the answers, as the quiz sets them.",
          "- Known reaction: typed into the quiz's reaction box and matched with the engine's own REACTIONS patterns.",
          "- Undertone \"don't know\": undertone not set (the quiz's \"Not sure\"), so matching assumes neutral.",
          "- Budget band: the largest Tune-your-plan option (₹400 / ₹700 / ₹1,200 / no limit) not above the band.",
          f"- Season: month {month} (0 = January), which the engine uses for winter dryness.",
          "- Concerns the quiz doesn't offer were dropped: " + ", ".join(f"{k} ({v})" for k, v in res["mapping_notes"].items()) + "."]
    (REPORTS / "eval_testset.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def before_after(res):
    b, A, B, C = res["compare"]["before"], res["A"], res["B"], res["C"]
    bt, at = b["A"]["tryon"], A["tryon"]
    rows = [("\"Your match\" = labelled best shade", f"{bt['overall']['exact_hit']}%", f"{at['overall']['exact_hit']}%"),
            ("Within 1 step of measured tone", f"{bt['overall']['within_1']}%", f"{at['overall']['within_1']}%"),
            ("Depth MAE", f"{bt['overall']['depth_mae']}", f"{at['overall']['depth_mae']}"),
            ("Band gap, within 1 of labelled best", f"{bt['band_gap']['within_1_of_best']} pts", f"{at['band_gap']['within_1_of_best']} pts"),
            ("Band gap, exact shade", f"{bt['band_gap']['exact_hit']} pts", f"{at['band_gap']['exact_hit']} pts"),
            ("Profiles with a MUST_NOT in a top 5", f"{b['B']['profiles_with_must_not_in_top5']}%", f"{B['profiles_with_must_not_in_top5']}%"),
            ("MUST_NOT blocked by check()", f"{b['B']['recall']}%", f"{B['recall']}%"),
            ("  on labels the quiz can know", f"{b['B']['recall_on_knowable_labels']['recall']}%", f"{B['recall_on_knowable_labels']['recall']}%"),
            ("GOOD in top 5 (hit rate)", f"{b['C']['hit_rate']}%", f"{C['overall']['hit_rate']}%")]
    return [f"## Before and after (vs `{res['compare']['ref']}`)", "", "| Measure | Before | After |", "|---|---|---|"] + [f"| {r[0]} | {r[1]} | {r[2]} |" for r in rows] + [""]


def visual(res, truth, cat):
    """same model face, predicted vs labelled best shade, 12 customers (4 per band, worst misses first)"""
    from PIL import Image, ImageDraw
    from playwright.sync_api import sync_playwright
    sys.path.insert(0, str(ROOT / "tests"))
    import quiz_flow_test as Q
    faces = json.loads((ROOT / "data/model_faces.json").read_text())["faces"]
    worst_ids = [w["customer_id"] for w in res["A"]["worst_misses"]]
    rows = {w["customer_id"]: w for w in res["A"]["_all"]}
    picked = []
    for b, lo, hi in BANDS:
        pool = [c for c in worst_ids if lo <= truth[c]["true_monk_tone"] <= hi]
        rest = sorted((r for r in rows.values() if lo <= r["true_tone"] <= hi and r["customer_id"] not in pool),
                      key=lambda r: (-abs(r["depth_error"]), r["customer_id"]))
        picked += (pool + [r["customer_id"] for r in rest])[:4]
    site = Q.build_offline()
    srv = Q.serve(site, 8899)
    cells = []
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=Q.CHROME)
        pg = br.new_page(viewport={"width": 1280, "height": 900})
        pg.goto("http://127.0.0.1:8899/index.html#try-on")
        pg.wait_for_timeout(500)
        for cid in picked:
            r, t = rows[cid], truth[cid]
            fi = min(range(len(faces)), key=lambda i: (abs(faces[i]["monk"] - t["true_monk_tone"]), faces[i]["undertone"] != t["true_undertone"]))
            if pg.is_visible(".to-tools [data-to=start]"):
                pg.click(".to-tools [data-to=start]")
            pg.click(f".to-model[data-i='{fi}']")
            pg.wait_for_timeout(250)
            imgs = []
            for i in (r["pred_i"], r["best_i"]):
                url = pg.evaluate("""([pid,i])=>{const p=BY_ID[pid],[name,depth,und,hex,cov]=p.s[i];
                    TRYON.state.look={base:{p,s:{name,depth,und,hex,cov,fin:p.fin||'natural',demo:false}}};TRYON.setSplit(0);TRYON._draw();
                    return document.querySelector('.to-cv').toDataURL('image/png')}""", [r["product"], i])
                import base64, io
                imgs.append(Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGB"))
            cells.append((cid, r, t, faces[fi], imgs))
        br.close()
    srv.shutdown()
    cw, ch, lab = 220, 275, 300
    sheet = Image.new("RGB", (lab + 2 * cw, 30 + ch * len(cells)), "white")
    d = ImageDraw.Draw(sheet)
    d.text((lab + 8, 8), "Predicted (\"Your match\")", fill=(60, 50, 40))
    d.text((lab + cw + 8, 8), "Labelled best shade", fill=(60, 50, 40))
    for k, (cid, r, t, f, imgs) in enumerate(cells):
        y = 30 + k * ch
        txt = [cid, f"self tone {r['self_tone']} / {r['self_undertone']}", f"true tone {t['true_monk_tone']} / {t['true_undertone']}",
               f"face: {f['label']}", f"pred: {r['predicted'][:44]}", f"best: {r['best'][:44]}", f"depth error {r['depth_error']:+}"]
        for j, s in enumerate(txt):
            d.text((8, y + 60 + j * 16), s, fill=(40, 30, 20) if j == 0 else (100, 90, 80))
        for c, im in enumerate(imgs):
            w, h = im.size
            crop = im.crop((int(w * .2), int(h * .12), int(w * .8), int(h * .7))).resize((cw, ch))
            sheet.paste(crop, (lab + c * cw, y))
    REPORTS.mkdir(exist_ok=True)
    sheet.save(REPORTS / "tryon_visual_check.png")
    return [{"customer_id": c[0], "face": c[3]["id"], "predicted": c[1]["predicted"], "best": c[1]["best"], "depth_error": c[1]["depth_error"]} for c in cells]


def main():
    month = None
    if "--month" in sys.argv:
        month = int(sys.argv[sys.argv.index("--month") + 1])
    inputs, truth, labels = load()
    cat = {p["id"]: p for p in json.loads((ROOT / "data/catalogue.json").read_text())}
    categories = sorted({l["category"] for l in labels if l["label"] != "BEST_SHADE"})
    eng = run_engine(inputs, categories, month)
    res = score(inputs, truth, labels, eng, cat)
    res["tryon_call"] = eng.get("tryon_call")
    if "--compare" in sys.argv:            # re-run an older engine + catalogue + try-on from git, for a before/after table
        ref = sys.argv[sys.argv.index("--compare") + 1]
        old = Path(tempfile.mkdtemp(prefix="aaina_eval_ref_"))
        for f in ("src/engine.js", "src/tryon.js", "data/catalogue.json", "data/calibration.json"):
            (old / f).parent.mkdir(parents=True, exist_ok=True)
            (old / f).write_bytes(subprocess.run(["git", "show", f"{ref}:{f}"], cwd=ROOT, capture_output=True, check=True).stdout)
        old_cat = {p["id"]: p for p in json.loads((old / "data/catalogue.json").read_text())}
        before = score(inputs, truth, labels, run_engine(inputs, categories, month, old), old_cat)
        res["compare"] = {"ref": ref, "before": {"A": {k: before["A"][k] for k in ("tryon",)}, "B": {k: before["B"][k] for k in
                          ("profiles_with_must_not_in_top5", "recall", "recall_on_knowable_labels")}, "C": before["C"]["overall"]}}
    write_reports(res, eng["month"])
    res["A"]["_all"] = sorted_all(inputs, truth, labels, eng, cat)       # every customer's pick, for the visual check
    if "--visual" in sys.argv:
        vis = visual(res, truth, cat)
        j = json.loads((REPORTS / "eval_testset.json").read_text())
        j["visual_check"] = vis
        (REPORTS / "eval_testset.json").write_text(json.dumps(j, indent=1, ensure_ascii=False))
    A, B, C = res["A"], res["B"], res["C"]
    print(json.dumps({"tryon": A["tryon"]["overall"], "gap": A["tryon"]["band_gap"], "baseline": A["baseline"]["overall"],
                      "safety_top5": B["profiles_with_must_not_in_top5"], "recall": B["recall"],
                      "relevance": C["overall"]}, ensure_ascii=False))


def sorted_all(inputs, truth, labels, eng, cat):
    """every customer's try-on pick in the worst_misses format"""
    by = {p["customer_id"]: p for p in eng["profiles"]}
    inp = {i["customer_id"]: i for i in inputs}
    out = []
    for l in labels:
        if l["label"] != "BEST_SHADE":
            continue
        cid, pid = l["customer_id"], l["product_id"]
        best_i = int(re.match(r"P\d+-S(\d+)", l["reason"]).group(1)) - 1
        sh = cat[pid]["s"]
        i = by[cid]["match"][pid]["tryon"]
        out.append({"customer_id": cid, "product": pid, "self_tone": inp[cid]["monk_tone_self"], "self_undertone": inp[cid]["undertone_self"],
                    "true_tone": truth[cid]["true_monk_tone"], "true_undertone": truth[cid]["true_undertone"],
                    "predicted": f"{pid}-S{i+1:02d} {sh[i][0]} (depth {sh[i][1]}, {sh[i][2]})",
                    "best": f"{pid}-S{best_i+1:02d} {sh[best_i][0]} (depth {sh[best_i][1]}, {sh[best_i][2]})",
                    "depth_error": sh[i][1] - truth[cid]["true_monk_tone"], "exact": i == best_i, "pred_i": i, "best_i": best_i})
    return out


if __name__ == "__main__":
    main()
