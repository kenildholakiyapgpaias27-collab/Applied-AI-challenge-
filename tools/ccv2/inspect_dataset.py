#!/usr/bin/env python3
"""Step 1 - inspect a downloaded Casual Conversations v2 folder before using it.

Nothing about the dataset's layout is assumed: this walks the folder, counts media files, opens every
annotation-looking file (.json/.jsonl/.csv/.tsv), and reports its fields, value types, examples and, for
low-cardinality fields, the full value counts (e.g. how many participants per Monk tone, per country).
It also writes a draft config.json with its best guess for each field the pipeline needs; check it.

    python3 inspect_dataset.py /path/to/ccv2 --out report_dir
"""
import argparse, collections, csv, json, pathlib, re, sys

NEED = {  # pipeline field -> name patterns to look for
    "participant": r"(subject|participant|person|user)[_ ]?id|^id$|^subject$",
    "video": r"video|file|path|clip|filename",
    "monk": r"monk|mst",
    "fitzpatrick": r"fitz",
    "country": r"country|nation|region|location",
    "lighting": r"light|illum|indoor|outdoor|setting|environment|scene",
    "device": r"device|camera|phone|recorder",
    "age": r"^age|age_",
    "gender": r"gender|sex",
}
MEDIA = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".jpg", ".jpeg", ".png"}

def flatten(d, pre=""):
    """Nested dicts become dotted keys: {"a": {"b": 1}} -> {"a.b": 1}. Lists are kept as values."""
    out = {}
    if not isinstance(d, dict): return {pre.rstrip(".") or "value": d}
    for k, v in d.items():
        key = f"{pre}{k}"
        if isinstance(v, dict): out.update(flatten(v, key + "."))
        else: out[key] = v
    return out

def records_from(path):
    s = path.suffix.lower()
    try:
        if s in (".csv", ".tsv"):
            with open(path, newline="", encoding="utf-8", errors="replace") as f:
                return list(csv.DictReader(f, delimiter="\t" if s == ".tsv" else ","))
        if s == ".jsonl":
            return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        if s == ".json":
            d = json.load(open(path, encoding="utf-8"))
            if isinstance(d, list): return d
            if isinstance(d, dict):
                lists = [v for v in d.values() if isinstance(v, list) and v and isinstance(v[0], dict)]
                if lists: return max(lists, key=len)
                if all(isinstance(v, dict) for v in d.values()): return [dict(v, _key=k) for k, v in d.items()]
                return [d]
    except Exception as e:
        print(f"  ! could not read {path}: {e}", file=sys.stderr)
    return []

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("root"); ap.add_argument("--out", default="ccv2_report"); a = ap.parse_args()
    root, out = pathlib.Path(a.root), pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ext = collections.Counter(); media = []; ann = []
    for p in root.rglob("*"):
        if not p.is_file(): continue
        ext[p.suffix.lower()] += 1
        if p.suffix.lower() in MEDIA: media.append(p)
        elif p.suffix.lower() in (".json", ".jsonl", ".csv", ".tsv"): ann.append(p)
    lines = [f"# Dataset inspection: {root}", "", f"Files by type: {dict(ext.most_common())}", f"Media files: {len(media)}", f"Annotation files: {len(ann)}", ""]
    best = {}
    for p in sorted(ann, key=lambda x: -x.stat().st_size)[:20]:
        recs = [flatten(r) if isinstance(r, dict) else {"value": r} for r in records_from(p)]
        if not recs: continue
        keys = collections.Counter(k for r in recs for k in r)
        lines += [f"## {p.relative_to(root)}  ({len(recs)} records)", "", "| field | filled | type | examples | value counts (if few) |", "|---|---|---|---|---|"]
        for k, n in keys.most_common():
            vals = [r[k] for r in recs if k in r and r[k] not in (None, "")]
            types = collections.Counter(type(v).__name__ for v in vals).most_common(2)
            uniq = collections.Counter(json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v for v in vals)
            ex = ", ".join(list(uniq)[:3])[:80]
            vc = ", ".join(f"{v}: {c}" for v, c in sorted(uniq.items(), key=lambda x: x[0])[:20]) if len(uniq) <= 20 else f"{len(uniq)} distinct"
            lines.append(f"| `{k}` | {n} | {'/'.join(t for t, _ in types)} | {ex} | {vc} |")
            for need, pat in NEED.items():
                if re.search(pat, k.split(".")[-1], re.I) and need not in best: best[need] = {"file": str(p.relative_to(root)), "field": k}
        lines.append("")
    cfg = {"dataset_root": str(root), "annotation_file": None, "fields": {}, "label_map": {str(i): i for i in range(1, 11)},
           "filters": {"country": None, "max_participants_per_tone": 60}, "frames_per_video": 4, "max_videos_per_participant": 3,
           "_note": "Check every field. label_map converts the dataset's Monk value to an Aaina tone (1-10); identity by default because Aaina's swatches are the Monk scale."}
    for need, v in best.items():
        cfg["fields"][need] = v["field"]; cfg["annotation_file"] = cfg["annotation_file"] or v["file"]
    lines += ["## Draft field mapping (verify before use)", "", "```json", json.dumps(cfg, indent=1), "```",
              "", "Fields the pipeline needs: participant, video (or a way to find it), monk. Optional: country, lighting, device, fitzpatrick."]
    (out / "schema_report.md").write_text("\n".join(lines), encoding="utf-8")
    (out / "config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    print("\n".join(lines[:8])); print(f"\nWrote {out/'schema_report.md'} and a draft {out/'config.json'}.")
    missing = [k for k in ("participant", "video", "monk") if k not in cfg["fields"]]
    if missing: print("Could not find fields for:", ", ".join(missing), "- set them in config.json by hand.")

if __name__ == "__main__": main()
