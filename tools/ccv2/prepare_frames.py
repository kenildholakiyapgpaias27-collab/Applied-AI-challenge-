#!/usr/bin/env python3
"""Step 2 - pick participants, extract frames and locate the face in each frame.

Uses the field mapping from config.json (made by inspect_dataset.py and checked by you).
- Balances participants per Monk tone (and filters by country, e.g. India, if set).
- Extracts N evenly spaced frames from up to M videos per participant with ffmpeg.
- Finds the face: MediaPipe face detection if installed (pip install mediapipe), otherwise a skin-colour
  blob near the centre (fine for talking-head videos; check the overlay images it writes).
Writes frames/ and manifest.csv (participant, video, frame, label, country, lighting, device, oval).

    python3 prepare_frames.py config.json --out work
"""
import argparse, csv, json, pathlib, random, subprocess, sys, collections
import numpy as np, cv2
sys.path.insert(0, str(pathlib.Path(__file__).parent)); from inspect_dataset import records_from, flatten

def duration(p):
    try: return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).decode().strip())
    except Exception: return None

def frames_from(p, n, outdir, stem):
    if p.suffix.lower() in (".jpg", ".jpeg", ".png"): return [p]
    d = duration(p) or 0; outs = []
    for k in range(n):
        t = d * (k + 1) / (n + 1) if d else k
        o = outdir / f"{stem}_f{k}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(p), "-frames:v", "1", "-vf", "scale='min(1280,iw)':-2", "-q:v", "2", str(o)], check=False)
        if o.exists(): outs.append(o)
    return outs

try:
    import mediapipe as mp; _mp = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
except Exception: _mp = None

def find_face(img):
    H, W = img.shape[:2]
    if _mp is not None:
        r = _mp.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if r.detections:
            b = max(r.detections, key=lambda d: d.score[0]).location_data.relative_bounding_box
            cx, cy, w, h = b.xmin + b.width / 2, b.ymin + b.height / 2, b.width * 1.05, b.height * 1.25
            return dict(cx=cx, cy=cy - 0.06 * h, w=w, h=h, how="mediapipe")
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32); L = lab[..., 0] * 100 / 255; a = lab[..., 1] - 128; b = lab[..., 2] - 128
    C = np.hypot(a, b); hue = np.degrees(np.arctan2(b, a))
    m = ((L > 6) & (L < 98) & (a > -1) & (b > 1.5) & (C > np.where(L < 35, 1.5, 3.5)) & (hue > 15) & (hue < 100)).astype(np.uint8)
    # walls can be skin-coloured: drop pixels that match the frame border's colour
    border = np.concatenate([lab[:8].reshape(-1, 3), lab[-8:].reshape(-1, 3), lab[:, :8].reshape(-1, 3), lab[:, -8:].reshape(-1, 3)])
    bmed = np.median(border, 0); m &= (np.linalg.norm(lab - bmed, axis=2) > 10).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8)); n, lbl, stats, cent = cv2.connectedComponentsWithStats(m)
    best = None
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 0.01 * W * H or w > 0.9 * W or not (0.45 < w / max(h, 1) < 1.4): continue
        score = area * (stats[i][4] / (w * h)) / (1 + np.hypot(cent[i][0] / W - 0.5, cent[i][1] / H - 0.45) * 4)
        if best is None or score > best[0]: best = (score, x, y, w, h)
    if not best: return None
    _, x, y, w, h = best; h = min(h, 1.35 * w)
    return dict(cx=(x + w / 2) / W, cy=(y + h / 2) / H, w=w / W, h=h / H, how="skin-blob")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("config"); ap.add_argument("--out", default="work"); ap.add_argument("--seed", type=int, default=7); a = ap.parse_args()
    cfg = json.load(open(a.config)); F = cfg["fields"]; root = pathlib.Path(cfg["dataset_root"]); out = pathlib.Path(a.out); (out / "frames").mkdir(parents=True, exist_ok=True); (out / "check").mkdir(exist_ok=True)
    recs = [flatten(r) for r in records_from(root / cfg["annotation_file"])]
    lm = {str(k): int(v) for k, v in cfg.get("label_map", {}).items()}
    def label(r):
        v = r.get(F["monk"]); v = v[0] if isinstance(v, list) and v else v
        try: v = str(int(float(v)))
        except Exception: return None
        return lm.get(v)
    flt = cfg.get("filters", {}); country = (flt.get("country") or "").lower()
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in recs:
        t = label(r)
        if not t: continue
        if country and country not in str(r.get(F.get("country", ""), "")).lower(): continue
        by[t][str(r.get(F["participant"]))].append(r)
    rnd = random.Random(a.seed); rows = []; cap = flt.get("max_participants_per_tone", 60)
    index = {p.name: p for p in root.rglob("*") if p.suffix.lower() in (".mp4", ".mov", ".mkv", ".avi", ".webm", ".jpg", ".jpeg", ".png")}
    for t in sorted(by):
        pids = sorted(by[t]); rnd.shuffle(pids)
        for pid in pids[:cap]:
            vids = by[t][pid][: cfg.get("max_videos_per_participant", 3)]
            for r in vids:
                vv = r.get(F["video"], ""); vv = vv if isinstance(vv, list) else [vv]
                vv = [x if isinstance(x, str) else next((s for s in (x.values() if isinstance(x, dict) else []) if isinstance(s, str) and "." in s), "") for x in vv]
                for v in vv:
                  p = root / v if v and (root / v).exists() else index.get(pathlib.Path(v).name) if v else None
                  if not p: continue
                  for fr in frames_from(p, cfg.get("frames_per_video", 4), out / "frames", f"{pid}_{p.stem}"):
                    img = cv2.imread(str(fr)); face = find_face(img) if img is not None else None
                    if not face: continue
                    if len(rows) < 40:  # a few overlays so you can check the face boxes
                        H, W = img.shape[:2]; chk = img.copy(); cv2.ellipse(chk, (int(face["cx"] * W), int(face["cy"] * H)), (int(face["w"] * W / 2), int(face["h"] * H / 2)), 0, 0, 360, (0, 255, 0), 3); cv2.imwrite(str(out / "check" / fr.name), chk)
                    rows.append(dict(participant=pid, video=p.name, frame=str(fr), label=t, country=r.get(F.get("country", ""), ""), lighting=r.get(F.get("lighting", ""), ""), device=r.get(F.get("device", ""), ""), oval=json.dumps({k: round(face[k], 4) for k in ("cx", "cy", "w", "h")}), face_how=face["how"]))
    with open(out / "manifest.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["participant"]); w.writeheader(); w.writerows(rows)
    c = collections.Counter(r["label"] for r in rows); pc = collections.Counter(); seen = set()
    for r in rows:
        if r["participant"] not in seen: seen.add(r["participant"]); pc[r["label"]] += 1
    print(f"{len(rows)} frames from {len(seen)} participants. Participants per tone: {dict(sorted(pc.items()))}. Frames per tone: {dict(sorted(c.items()))}")
    thin = [t for t in range(1, 11) if pc.get(t, 0) < 20]
    if thin: print("Fewer than 20 participants for tones:", thin, "- results for these will be unreliable; the mapping keeps them close to the library swatch.")

if __name__ == "__main__": main()
