#!/usr/bin/env python3
"""Step 4 - learn the mapping layer onto the Aaina shade library, validate it, and write calibration.json.

What is learned: for each Aaina tone (1-10), where faces labelled with that tone actually land in the reader's
corrected colour space under real cameras and lighting (a centroid). Centroids are shrunk towards the library
swatch (k pseudo-observations), so tones with few photos stay at the library colour, and L* is kept in order
(lighter tone = higher L*). The library stays the ground truth: a photo always maps to the closest existing
tone; no new category can appear. Product shades are then chosen by colour similarity within the library.

Validation: 5-fold cross-validation grouped by participant (the same person is never in train and test),
compared with the current mapping (swatches only). Reports exact, within-one, off-by-two-or-more, per tone,
per country/lighting/device when present, per-participant consistency and recapture rate.

    python3 train_mapping.py work/features.csv --out calibration.json --report report.md
"""
import argparse, csv, json, math, collections, datetime
import numpy as np

SWATCH_HEX = {1:"#f6ede4",2:"#f3e7db",3:"#f7ead0",4:"#eadaba",5:"#d7bd96",6:"#a07e56",7:"#825c43",8:"#604134",9:"#3a312a",10:"#292420"}
def srgb2lab(h):
    rgb = [int(h[i:i+2], 16) / 255 for i in (1, 3, 5)]; lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    X = (lin[0]*0.4124 + lin[1]*0.3576 + lin[2]*0.1805) / 0.95047; Y = lin[0]*0.2126 + lin[1]*0.7152 + lin[2]*0.0722; Z = (lin[0]*0.0193 + lin[1]*0.1192 + lin[2]*0.9505) / 1.08883
    f = lambda t: t ** (1/3) if t > 0.008856 else 7.787 * t + 16/116
    return np.array([116*f(Y) - 16, 500*(f(X) - f(Y)), 200*(f(Y) - f(Z))])
SW = {t: srgb2lab(h) for t, h in SWATCH_HEX.items()}

def tone_dist(x, y):  # same distance as the page (lightness weighted fully, chroma and hue at half)
    L1, C1, h1 = x[0], math.hypot(x[1], x[2]), math.degrees(math.atan2(x[2], x[1])); L2, C2, h2 = y[0], math.hypot(y[1], y[2]), math.degrees(math.atan2(y[2], y[1]))
    dH = 2 * math.sqrt(max(C1 * C2, 0)) * math.sin(math.radians(h1 - h2) / 2)
    return math.hypot(L1 - L2, 0.5 * (C1 - C2), 0.5 * dH)

def fit(X, y, k, g=None):
    """Centroid per tone from per-PERSON averages (frames of one person are not independent), shrunk towards
    the library swatch with k pseudo-people, then lightness made monotonic (pool-adjacent-violators)."""
    C, W = {}, {}
    for t in range(1, 11):
        m = y == t
        if g is not None and m.any():
            people = [X[m & (g == p)].mean(0) for p in sorted(set(g[m]))]
        else:
            people = list(X[m])
        n = len(people); W[t] = n + k
        C[t] = (np.sum(people, 0) + k * SW[t]) / (n + k) if n else SW[t].copy()
    # lightness must fall as the tone number rises: weighted isotonic (decreasing) fit on L*
    blocks = [[C[t][0], W[t], [t]] for t in range(1, 11)]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] < blocks[i + 1][0]:
            v = (blocks[i][0] * blocks[i][1] + blocks[i + 1][0] * blocks[i + 1][1]) / (blocks[i][1] + blocks[i + 1][1])
            blocks[i] = [v, blocks[i][1] + blocks[i + 1][1], blocks[i][2] + blocks[i + 1][2]]; del blocks[i + 1]; i = max(0, i - 1)
        else: i += 1
    for v, _, ts in blocks:
        for t in ts: C[t][0] = v
    return C

def predict(C, X): return np.array([min(C, key=lambda t: tone_dist(x, C[t])) for x in X])

def metrics(y, p, groups=None):
    n = len(y); d = np.abs(y - p)
    out = dict(n=int(n), exact=round(100 * float((d == 0).mean()), 1) if n else None, within1=round(100 * float((d <= 1).mean()), 1) if n else None, off2plus=round(100 * float((d >= 2).mean()), 1) if n else None)
    if groups is not None and n:
        by = collections.defaultdict(list)
        for g, q in zip(groups, p): by[g].append(q)
        out["consistency"] = round(100 * np.mean([collections.Counter(v).most_common(1)[0][1] / len(v) for v in by.values()]), 1)
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("features"); ap.add_argument("--out", default="calibration.json"); ap.add_argument("--report", default="report.md"); ap.add_argument("--k", type=float, default=3, help="pseudo-people pulling each tone towards its library swatch"); ap.add_argument("--source", default="Casual Conversations v2"); a = ap.parse_args()
    rows = list(csv.DictReader(open(a.features))); total = len(rows)
    ok = [r for r in rows if r["status"] == "OK" and r["L"] != ""]
    X = np.array([[float(r["L"]), float(r["a"]), float(r["b"])] for r in ok]); y = np.array([int(r["label"]) for r in ok]); g = np.array([r["participant"] for r in ok])
    pids = sorted(set(g)); rng = np.random.default_rng(7); rng.shuffle(pids); fold = {p: i % 5 for i, p in enumerate(pids)}; f = np.array([fold[p] for p in g])
    base, cal = np.zeros_like(y), np.zeros_like(y)
    for k in range(5):
        tr, te = f != k, f == k; C = fit(X[tr], y[tr], a.k, g[tr]); cal[te] = predict(C, X[te]); base[te] = predict(SW, X[te])
    R = {"photos_total": total, "recapture_rate": round(100 * (1 - len(ok) / max(1, total)), 1), "participants": len(pids),
         "current_mapping": metrics(y, base, g), "learned_mapping": metrics(y, cal, g), "per_tone": {}, "slices": {}}
    for t in range(1, 11):
        m = y == t; R["per_tone"][t] = {"participants": len(set(g[m])), "current": metrics(y[m], base[m]), "learned": metrics(y[m], cal[m])}
    for col in ("country", "lighting", "device"):
        vals = collections.Counter(r.get(col, "") for r in ok)
        if len([v for v in vals if v]) > 1:
            R["slices"][col] = {v: {"current": metrics(y[np.array([r.get(col, "") == v for r in ok])], base[np.array([r.get(col, "") == v for r in ok])]),
                                    "learned": metrics(y[np.array([r.get(col, "") == v for r in ok])], cal[np.array([r.get(col, "") == v for r in ok])])} for v in vals if v}
    C = fit(X, y, a.k, g); resid = [tone_dist(x, C[t]) for x, t in zip(X, y)]; tau = float(np.median(resid)) if resid else 4.0
    cal_json = {"source": f"{a.source} ({datetime.date.today().isoformat()})", "tau": round(max(2.0, tau), 2), "k": a.k,
                "n": {t: int((y == t).sum()) for t in range(1, 11)}, "centroids": {t: [round(float(v), 2) for v in C[t]] for t in range(1, 11)}}
    json.dump(cal_json, open(a.out, "w"), indent=1)
    L = [f"# Skin tone mapping report ({cal_json['source']})", "", f"Photos: {total}, readable: {len(ok)} (recapture rate {R['recapture_rate']}%), participants: {len(pids)}.",
         "Validation: 5-fold, grouped by participant.", "", "| mapping | exact | within one | off by 2+ | consistency |", "|---|---|---|---|---|"]
    for name, key in (("Current (library swatches)", "current_mapping"), ("Learned (this data)", "learned_mapping")):
        m = R[key]; L.append(f"| {name} | {m['exact']}% | {m['within1']}% | {m['off2plus']}% | {m.get('consistency')}% |")
    L += ["", "## Per tone", "", "| tone | participants | current exact | learned exact | learned within one |", "|---|---|---|---|---|"]
    for t, v in R["per_tone"].items(): L.append(f"| {t} | {v['participants']} | {v['current']['exact']}% | {v['learned']['exact']}% | {v['learned']['within1']}% |")
    for col, vs in R["slices"].items():
        L += ["", f"## By {col}", "", "| value | photos | current exact | learned exact |", "|---|---|---|---|"]
        for v, m in vs.items(): L.append(f"| {v} | {m['learned']['n']} | {m['current']['exact']}% | {m['learned']['exact']}% |")
    L += ["", f"Wrote `{a.out}`. Rebuild the page (python3 build.py) to use it. Tones with few participants stay near the library swatch (k={a.k})."]
    open(a.report, "w").write("\n".join(L)); json.dump(R, open(a.report.rsplit(".", 1)[0] + ".json", "w"), indent=1)
    print("\n".join(L[:12]))
if __name__ == "__main__": main()
