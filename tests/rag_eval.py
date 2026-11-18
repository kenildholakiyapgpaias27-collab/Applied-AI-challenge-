#!/usr/bin/env python3
"""Retrieval evaluation for the hybrid RAG layer: measures what each stage buys, on labelled queries.

    OPENAI_API_KEY=... python3 tests/rag_eval.py        # dense + hybrid configs (embeds the catalogue once, cached)
    python3 tests/rag_eval.py                           # without a key: BM25-only configs

Each query has a relevance rule over the catalogue (category / price cap / skin type / concern / ingredient).
Metrics over the top 5 results: P@5 (share that are relevant), MRR (how early the first relevant one appears).
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import rag_service as R  # noqa: E402


def blob(p):
    return ((p.get("a") or "") + " " + (p.get("i") or "")).lower()


def cat(*cs):
    return lambda p: p["c"] in cs


def all_of(*fs):
    return lambda p: all(f(p) for f in fs)


def price(n):
    return lambda p: (p.get("p") or 0) <= n


def skin(s):
    return lambda p: s in (p.get("st") or [])


def con(c):
    return lambda p: c in (p.get("con") or [])


def ing(*subs):
    return lambda p: any(s in blob(p) for s in subs)


QUERIES = [
    ("lipstick under 1000", all_of(cat("Lipstick"), price(1000))),
    ("show me kajals", cat("Kajal / eyeliner")),
    ("cheapest blush", cat("Blush")),
    ("sunscreen for oily skin under 500", all_of(cat("Sunscreen"), skin("oily"), price(500))),
    ("niacinamide serum", all_of(cat("Serum"), ing("niacinamide"))),
    ("something to stop midday shine", con("oiliness")),
    ("moisturiser for very dry skin", all_of(cat("Moisturiser"), skin("dry"))),
    ("vitamin c for dullness", ing("ascorb")),
    ("cleanser for acne prone skin", all_of(cat("Cleanser"), con("acne"))),
    ("lip balm", cat("Lip care")),
    ("foundation under 800", all_of(cat("Foundation"), price(800))),
    ("salicylic acid for blackheads", ing("salicylic")),
    ("eye cream for dark circles", cat("Eye cream")),
    ("retinol for fine lines", ing("retin", "bakuchiol")),
    ("hyaluronic acid for dehydration", ing("hyaluron")),
    ("face mask for dark spots under 800", all_of(cat("Face mask"), price(800))),
    ("primer", cat("Primer")),
    ("compact powder for oily skin", all_of(cat("Compact powder"), skin("oily"))),
    ("toner for pimples", all_of(cat("Toner"), con("acne"))),
    ("serum for pigmentation under 700", all_of(cat("Serum"), con("pigmentation"), price(700))),
    ("gel for a pimple", cat("Spot treatment")),
    ("scrub to remove dead skin", cat("Exfoliant")),
    ("glow boosting product", con("dullness")),
    ("moisturiser under 400", all_of(cat("Moisturiser"), price(400))),
    ("bb cream", cat("BB / CC cream")),
    ("face oil for dry skin", all_of(cat("Face oil"), skin("dry"))),
    ("sun protection for oily skin", all_of(cat("Sunscreen"), skin("oily"))),
]

# Written BEFORE looking at any result, with none of the catalogue's own words or the synonym table in mind: open-vocabulary paraphrases.
# This is the set that shows what the embeddings add; the main QUERIES were used to tune patterns, so they flatter the pipeline.
HELDOUT = [
    ("my t-zone gets greasy by the afternoon", con("oiliness")),
    ("I want my face to look radiant", con("dullness")),
    ("something calming for irritated cheeks", con("redness")),
    ("help with tiny bumps and clogged pores", con("acne")),
    ("protect me while I am outdoors all day", cat("Sunscreen")),
    ("make the puffiness and shadows under my eyes less visible", cat("Eye cream")),
    ("keep my lips from cracking in winter", cat("Lip care")),
    ("fade the marks my breakouts left behind", con("pigmentation")),
    ("firm up and smooth my skin as I get older", con("fine lines")),
    ("my skin feels tight and flaky after washing", con("dehydration")),
    ("something rich to put on before bed", cat("Moisturiser")),
    ("a natural-looking base for everyday", cat("Foundation", "BB / CC cream")),
]

CONFIGS = [
    # name,                          chunking, methods,            filters, facets, needs dense
    ("baseline: 1 chunk, hybrid",     "single", ("bm25", "dense"), False, False, True),
    ("BM25 only (2 chunks)",          "multi",  ("bm25",),         False, False, False),
    ("dense only (2 chunks)",         "multi",  ("dense",),        False, False, True),
    ("hybrid RRF (2 chunks)",         "multi",  ("bm25", "dense"), False, False, True),
    ("hybrid + facets",               "multi",  ("bm25", "dense"), False, True,  True),
    ("FULL: hybrid+filters+facets",   "multi",  ("bm25", "dense"), True,  True,  True),
    ("BM25 + filters + facets",       "multi",  ("bm25",),         True,  True,  False),
    ("FULL but 1 chunk per product",  "single", ("bm25", "dense"), True,  True,  True),
    ("FULL lean chunk (no INCI)",     "lean",   ("bm25", "dense"), True,  True,  True),
    ("dense only, lean chunk",        "lean",   ("dense",),        False, False, True),
]


def evaluate(idx, methods, filters, facets, queries=None):
    p5s, mrrs, per = [], [], []
    for q, rel in (queries or QUERIES):
        res = idx.search(q, 5, set(), methods=methods, filters=filters, facets=facets)["idx"]
        flags = [bool(rel(idx.products[i])) for i in res]
        p5 = (sum(flags) / 5.0) if res else 0.0
        mrr = next((1.0 / (n + 1) for n, f in enumerate(flags) if f), 0.0)
        p5s.append(p5)
        mrrs.append(mrr)
        per.append((q, p5, [idx.products[i]["n"][:30] for i in res][:3]))
    return sum(p5s) / len(p5s), sum(mrrs) / len(mrrs), per


def main():
    products = json.loads(R.CATALOGUE.read_text())
    emb = R._openai_embedder()
    idxs = {}
    for name, chunking, methods, flt, fac, dense in CONFIGS:
        if dense and not emb:
            print("%-32s skipped (set OPENAI_API_KEY for dense runs)" % name)
            continue
        idx = idxs.setdefault(chunking, R.Index(products, emb, chunking))
        p5, mrr, per = evaluate(idx, methods, flt, fac)
        hp5, hmrr, _ = evaluate(idx, methods, flt, fac, HELDOUT)
        print("%-32s tuned set P@5 %.3f MRR %.3f   |   HELD-OUT P@5 %.3f MRR %.3f" % (name, p5, mrr, hp5, hmrr))
        if os.environ.get("EVAL_VERBOSE"):
            for q, s, top in per:
                if s < 0.6:
                    print("     weak: %-40s P@5 %.1f  %s" % (q, s, top))


if __name__ == "__main__":
    main()
