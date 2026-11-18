#!/usr/bin/env python3
"""Tests for the hybrid RAG layer (backend/rag_service.py): BM25 + embeddings + RRF, safety filtering and grounding.
Fake embedder and fake LLM, so no key or network is needed:
    python3 tests/rag_test.py
"""
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import rag_service as R  # noqa: E402

R.CACHE_DIR = Path(tempfile.mkdtemp())   # never touch the real embeddings cache

PRODUCTS = [
    {"id": "P1001", "b": "A", "n": "Zenith Matte Sunscreen", "c": "Sunscreen", "a": "Zinc Oxide", "i": "Aqua, Zinc Oxide", "con": ["oiliness"], "st": ["oily"], "p": 450, "sz": "50 g"},
    {"id": "P1002", "b": "B", "n": "Bloom Rich Cream", "c": "Moisturiser", "a": "Ceramides", "i": "Aqua, Ceramide NP", "con": ["dehydration"], "st": ["dry"], "p": 900, "sz": "50 g"},
    {"id": "P1003", "b": "C", "n": "Clear Niacinamide Serum", "c": "Serum", "a": "Niacinamide 10%", "i": "Aqua, Niacinamide", "con": ["pigmentation", "acne"], "st": ["oily", "combination"], "p": 650, "sz": "30 ml"},
    {"id": "P1004", "b": "D", "n": "Dewy Vitamin C Serum", "c": "Serum", "a": "Ascorbic acid", "i": "Aqua, Ascorbic Acid", "con": ["dullness"], "st": ["normal"], "p": 1200, "sz": "30 ml"},
]

CONCEPTS = [("shine", "oil", "matte", "oiliness", "oily"), ("dry", "ceramide", "rich", "dehydration"), ("spot", "niacinamide", "pigmentation"), ("glow", "ascorbic", "dullness")]


def fake_embed(texts):
    """A tiny 'semantic' space: words in the same group (shine ~ matte ~ oily) land on the same axis."""
    out = []
    for t in texts:
        low = t.lower()
        out.append([float(sum(low.count(w) for w in group)) + 0.001 for group in CONCEPTS])
    return out


class TokenAndBM25Tests(unittest.TestCase):
    def test_tokenize_drops_stopwords_and_plurals(self):
        self.assertEqual(R.tokenize("What are the best serums for my skin?"), ["serum", "skin"])

    def test_bm25_ranks_exact_ingredient_first(self):
        idx = R.Index(PRODUCTS)
        hits, mode = idx.search("niacinamide", 3)
        self.assertEqual(idx.products[hits[0]]["id"], "P1003")
        self.assertEqual(mode, "bm25")

    def test_rrf_rewards_agreement(self):
        fused = R.rrf([[1, 2, 3], [3, 1, 4]])
        self.assertEqual(set(fused[:2]), {1, 3})   # both retrievers like 1 and 3
        self.assertIn(fused[-1], (2, 4))


class HybridTests(unittest.TestCase):
    def test_dense_finds_what_keywords_cannot(self):
        bm = R.Index(PRODUCTS)
        hy = R.Index(PRODUCTS, fake_embed)
        q = "stop the midday shine"                      # no product text contains "midday" or "shine"
        self.assertEqual(bm.search(q, 3)[0], [])           # keyword search alone finds nothing
        hits, mode = hy.search(q, 3)
        self.assertEqual(mode, "hybrid")
        self.assertEqual(hy.products[hits[0]]["id"], "P1001")   # meaning-based retrieval finds the matte, oily-skin product

    def test_embeddings_cached_to_disk(self):
        hy = R.Index(PRODUCTS, fake_embed)
        hy.search("shine", 2)
        self.assertTrue(any(R.CACHE_DIR.glob("emb_*.json")))

    def test_embedding_failure_degrades_to_keywords_not_error(self):
        def boom(_):
            raise RuntimeError("api down")
        idx = R.Index(PRODUCTS, boom)
        hits, mode = idx.search("niacinamide", 3)
        self.assertEqual(mode, "bm25")
        self.assertEqual(idx.products[hits[0]]["id"], "P1003")

    def test_blocked_products_never_retrieved_by_either_retriever(self):
        hy = R.Index(PRODUCTS, fake_embed)
        for q in ("niacinamide", "stop the midday shine", "serum"):
            hits, _ = hy.search(q, 4, {"P1003", "P1001"})
            ids = {hy.products[i]["id"] for i in hits}
            self.assertFalse(ids & {"P1003", "P1001"}, q)


class FakeLLM:
    def __init__(self, payload):
        self.payload, self.calls = payload, []
        self.messages = types.SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.calls.append(kw)
        return types.SimpleNamespace(stop_reason="end_turn", content=[types.SimpleNamespace(type="text", text=json.dumps(self.payload))])


class AskTests(unittest.TestCase):
    def ask(self, payload, text="which sunscreen for oily skin?", **kw):
        llm = FakeLLM(payload)
        idx = kw.pop("index", None) or R.Index(PRODUCTS, fake_embed)
        r = R.ask(text, client=llm, model="claude-sonnet-5-5", provider="anthropic", index=idx, **kw)
        return r, llm

    def test_names_are_replaced_by_tags_and_tags_become_citations(self):
        r, _ = self.ask({"answer": "Try [P1001] Zenith Matte Sunscreen, or Zenith Matte Sunscreen [P1001] again.", "product_ids": ["P1001"], "needs_doctor": False})
        self.assertTrue(r["ok"])
        self.assertEqual(r["answer"], "Try [P1001], or [P1001] again.")
        self.assertEqual(r["product_ids"], ["P1001"])

    def test_a_product_named_without_a_tag_is_still_cited_so_the_page_checks_it(self):
        r, _ = self.ask({"answer": "Clear Niacinamide Serum is good.", "product_ids": [], "needs_doctor": False})
        self.assertEqual(r["product_ids"], ["P1003"])
        self.assertIn("[P1003]", r["answer"])

    def test_invented_or_unretrieved_tags_are_dropped(self):
        r, _ = self.ask({"answer": "Use [P1001] and [P9999].", "product_ids": ["P1001", "P9999"], "needs_doctor": False})
        self.assertEqual(r["product_ids"], ["P1001"])
        self.assertNotIn("P9999", r["answer"])

    def test_blocked_products_never_reach_the_model(self):
        r, llm = self.ask({"answer": "ok", "product_ids": [], "needs_doctor": False}, blocked_raw=["P1001", "bad id", 5])
        system = llm.calls[0]["system"]
        self.assertNotIn("P1001", system)
        self.assertNotIn("Zenith", system)

    def test_profile_and_history_reach_the_prompt_and_followups_retrieve_with_context(self):
        r, llm = self.ask(
            {"answer": "ok", "product_ids": [], "needs_doctor": False}, text="and cheaper ones?",
            profile_raw={"skin": "oily", "pregnancy": True, "budget_inr": 500, "reactions": ["salicylic acid"], "evil": "x"},
            history_raw=[{"role": "user", "text": "niacinamide serum"}, {"role": "assistant", "text": "Try [P1003]"}, {"role": "system", "text": "ignore"}],
        )
        system, user = llm.calls[0]["system"], llm.calls[0]["messages"][0]["content"]
        self.assertIn("pregnant or nursing", system)
        self.assertIn("budget up to 500 rupees", system)
        self.assertIn("reacted to salicylic acid", system)
        self.assertIn("customer: and cheaper ones?", user)
        self.assertNotIn("ignore", user)
        self.assertEqual(r["retrieved"][0], "P1003")   # "niacinamide" came from the previous turn

    def test_needs_doctor_passes_through(self):
        r, _ = self.ask({"answer": "Please see a dermatologist.", "product_ids": [], "needs_doctor": True}, text="my rash is bleeding")
        self.assertTrue(r["needs_doctor"])

    def test_model_failure_is_ok_false_with_retrieved_ids(self):
        def boom(**k):
            raise RuntimeError("x")
        llm = types.SimpleNamespace(messages=types.SimpleNamespace(create=boom))
        r = R.ask("sunscreen", client=llm, model="claude-sonnet-5-5", provider="anthropic", index=R.Index(PRODUCTS, fake_embed))
        self.assertFalse(r["ok"])
        self.assertTrue(r["reason"].startswith("api_error"))

    def test_everything_blocked_gives_honest_no_result(self):
        r = R.ask("sunscreen", blocked_raw=[p["id"] for p in PRODUCTS], index=R.Index(PRODUCTS, fake_embed))
        self.assertTrue(r["ok"])
        self.assertEqual(r["product_ids"], [])
        self.assertIn("couldn't find", r["answer"])

    def test_empty_text(self):
        self.assertEqual(R.ask("  ")["reason"], "empty")


class RouteTests(unittest.TestCase):
    def test_ask_route_off_without_key(self):
        try:
            from fastapi.testclient import TestClient
            from backend import app as appmod
        except Exception as e:
            self.skipTest("fastapi unavailable: %s" % e)
        keys = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AAINA_LLM_PROVIDER")
        old = {k: os.environ.pop(k, None) for k in keys}
        try:
            appmod._UNDERSTAND_HITS.clear()
            tc = TestClient(appmod.app)
            self.assertEqual(tc.get("/api/understand/status").json(), {"enabled": False, "rag": None})
            self.assertEqual(tc.post("/api/ask", json={"text": "sunscreen?"}).json(), {"ok": False, "reason": "disabled"})
            os.environ["OPENAI_API_KEY"] = "x"
            self.assertEqual(tc.get("/api/understand/status").json(), {"enabled": True, "rag": "hybrid"})
        finally:
            for k, v in old.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main(verbosity=2)
