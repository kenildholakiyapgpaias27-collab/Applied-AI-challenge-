#!/usr/bin/env python3
"""Build data/embeddings.json from data/catalogue.json.

One embedding per product. Uses OpenAI text-embedding-3-small (1536 dims,
cheap). The chunk text follows docs/CATALOGUE_STRUCTURE.md §4.

Run whenever data/catalogue.json changes:

    export OPENAI_API_KEY=sk-proj-...
    python3 tools/build_embeddings.py
    python3 build.py

Cost: ~806 products × ~120 tokens ≈ 100k tokens → ~$0.002 at current
text-embedding-3-small pricing. Takes about 15 seconds.

No external dependencies — uses only urllib. Batches to 100 inputs per call.
"""
import hashlib, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = "text-embedding-3-small"
DIM   = 1536
BATCH = 100

def unpack_flags(fl: str) -> dict:
    # see docs/CATALOGUE_STRUCTURE.md §2 — "Packed flags"
    names = ["fragrance", "essential_oils", "drying_alcohol",
             "retinoid", "aha", "bha", "pregnancy_caution"]
    return {n: (i < len(fl) and fl[i] == "1") for i, n in enumerate(names)}

def pretty_flags(p: dict) -> str:
    bits = []
    f = unpack_flags(p.get("fl", ""))
    bits.append("fragrance" if f["fragrance"] else "fragrance-free")
    bits.append("contains essential oils" if f["essential_oils"] else "no essential oils")
    if f["retinoid"]: bits.append("contains retinoid")
    if f["aha"]:      bits.append("contains AHA")
    if f["bha"]:      bits.append("contains BHA")
    if f["pregnancy_caution"]: bits.append("pregnancy-cautioned")
    com = p.get("com")
    if com: bits.append(f"{com} comedogenic risk")
    return ", ".join(bits)

def chunk_text(p: dict) -> str:
    inci = (p.get("i") or "").split(",")
    inci_short = ", ".join(x.strip() for x in inci[:12])
    bits = [
        f'{p.get("b","")} {p.get("n","")} ({p.get("c","")})',
        f'key actives: {p.get("a") or "none declared"}',
        f'concerns: {", ".join(p.get("con", []))}',
        f'suits: {", ".join(p.get("st", []))}',
        pretty_flags(p),
        f'₹{p.get("p","?")} for {p.get("sz","")}',
    ]
    if p.get("spf"): bits.append(f'SPF {p["spf"]}')
    if p.get("fin"): bits.append(f'finish: {p["fin"]}')
    if inci_short:   bits.append(f'ingredients: {inci_short}')
    return " | ".join(b for b in bits if b)

def embed_batch(key: str, texts: list[str]) -> list[list[float]]:
    body = json.dumps({"model": MODEL, "input": texts}).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
                return [d["embedding"] for d in data["data"]]
        except urllib.error.HTTPError as e:
            # rate-limit or transient server error → backoff
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(2 ** attempt)
                continue
            raise

def main() -> int:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr); return 2

    cat_path = ROOT / "data" / "catalogue.json"
    if not cat_path.exists():
        print(f"ERROR: {cat_path} missing", file=sys.stderr); return 2

    catalogue = json.loads(cat_path.read_text())
    cat_hash  = hashlib.sha256(cat_path.read_bytes()).hexdigest()[:12]
    print(f"Catalogue: {len(catalogue)} products, hash {cat_hash}")

    items = []
    for i in range(0, len(catalogue), BATCH):
        batch = catalogue[i:i+BATCH]
        texts = [chunk_text(p) for p in batch]
        print(f"  embedding {i}..{i+len(batch)} ({len(texts)} items)")
        vecs = embed_batch(key, texts)
        for p, t, v in zip(batch, texts, vecs):
            # round to 6 d.p. to halve the JSON size with ~no retrieval impact
            items.append({"id": p["id"], "text": t, "vec": [round(x, 6) for x in v]})

    out = {
        "model":    MODEL,
        "dim":      DIM,
        "cat_hash": cat_hash,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "items":    items,
    }
    out_path = ROOT / "data" / "embeddings.json"
    out_path.write_text(json.dumps(out, separators=(",", ":")))
    kb = out_path.stat().st_size / 1024
    print(f"Wrote {out_path} ({kb:.0f} KB, {len(items)} vectors)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
