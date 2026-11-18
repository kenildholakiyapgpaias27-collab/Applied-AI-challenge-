#!/usr/bin/env python3
"""Tests for the hybrid RAG layer (backend/rag_service.py): query parsing, hard filters, BM25 + embeddings + RRF,
safety blocking, grounding and failure behaviour. Fake embedder and fake LLM, so no key or network is needed:
    python3 tests/rag_test.py
(Retrieval QUALITY is measured separately by tests/rag_eval.py.)
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
    {"id": "P1005", "b": "E", "n": "Petal Creme Lipstick", "c": "Lipstick", "a": "", "i": "Ricinus Communis Seed Oil, Mica", "con": [], "st": ["oily", "dry"], "p": 389, "sz": "3.5 g"},
    {"id": "P1006", "b": "F", "n": "Velvet Matte Lipstick", "c": "Lipstick", "a": "", "i": "Cera Alba, Mica", "con": [], "st": ["oily", "dry"], "p": 1500, "sz": "3.5 g"},
    {"id": "P1007", "b": "G", "n": "Noor Smudgeproof Kajal", "c": "Kajal / eyeliner", "a": "", "i": "Carbon Black", "con": [], "st": ["oily", "dry"], "p": 249, "sz": "1 g"},
    {"id": "P1008", "b": "H", "n": "Calm Centella Serum", "c": "Serum", "a": "Centella", "i": "Aqua, Centella Asiatica", "con": ["redness"], "st": ["dry", "normal"], "p": 700, "sz": "30 ml"},
    {"id": "P1009", "b": "I", "n": "Lip Night Mask", "c": "Lip care", "a": "", "i": "Shea Butter", "con": [], "st": ["dry"], "p": 299, "sz": "10 g"},
]

CONCEPTS = [("shine", "oil", "matte", "oiliness", "oily", "greasy"), ("dry", "ceramide", "rich", "dehydration"), ("spot", "niacinamide", "pigmentation"),
            ("glow", "ascorbic", "dullness"), ("calm", "angry", "centella", "redness")]


def fake_embed(texts):
    """A tiny 'semantic' space: words in the same group land on the same axis."""
    return [[float(sum(t.lower().count(w) for w in group)) + 0.001 for group in CONCEPTS] for t in texts]


def ids(idx, res):
    return [idx.products[i]["id"] for i in res["idx"]]


class QueryTests(unittest.TestCase):
    def test_categories_and_price_caps(self):
        q = R.Query("a pink lipstick under 1000")
        self.assertEqual(q.categories, ["Lipstick"])
        self.assertEqual(q.max_price, 1000)
        self.assertNotIn("1000", q.clean)
        self.assertNotIn("lipstick", q.clean.lower())
        for text, cap in (("serum below ₹500", 500), ("moisturiser less than 1k", 1000), ("sunscreen within Rs. 750", 750),
                          ("toner 400 rupees or less", 400), ("cleanser up to 1,200", 1200)):
            self.assertEqual(R.Query(text).max_price, cap, text)
        self.assertIsNone(R.Query("serum for dark spots").max_price)

    def test_category_overlaps_resolve_correctly(self):
        self.assertEqual(R.Query("a lip mask").categories, ["Lip care"])          # not "Face mask"
        self.assertEqual(R.Query("eye cream for puffiness").categories, ["Eye cream"])   # not "Moisturiser"
        self.assertEqual(R.Query("a bb cream").categories, ["BB / CC cream"])
        self.assertEqual(R.Query("sun protection").categories, ["Sunscreen"])
        self.assertEqual(R.Query("gel for a pimple").categories, ["Spot treatment"])
        self.assertEqual(R.Query("something for my skin").categories, [])

    def test_cheapest_skins_and_concerns(self):
        q = R.Query("cheapest serum for oily skin and pimples")
        self.assertTrue(q.cheapest)
        self.assertIn("oily", q.skins)
        self.assertIn("acne", q.concerns)

    def test_tokenize_drops_stopwords_and_plurals(self):
        self.assertEqual(R.tokenize("What are the best serums for my skin?"), ["serum", "skin"])


class ChunkingTests(unittest.TestCase):
    def test_modes(self):
        p = PRODUCTS[2]
        self.assertEqual(len(R.make_chunks(p)), 1)                       # default: one chunk per product (measured best)
        self.assertEqual(len(R.make_chunks(p, "multi")), 2)
        self.assertNotIn("Ingredients", R.make_chunks(p, "lean")[0])


class FilterTests(unittest.TestCase):
    def test_hard_filters_hold_for_every_result(self):
        idx = R.Index(PRODUCTS)
        r = idx.search("lipstick under 1000", 8)
        self.assertEqual(ids(idx, r), ["P1005"])                          # the Rs 1,500 lipstick and every non-lipstick are excluded
        self.assertEqual(r["filters"], {"categories": ["Lipstick"], "max_price": 1000, "cheapest": False})
        self.assertIsNone(r["relaxed"])

    def test_pure_filter_query_is_cheapest_first(self):
        idx = R.Index(PRODUCTS)
        self.assertEqual(ids(idx, idx.search("show me lipsticks", 8)), ["P1005", "P1006"])

    def test_cheapest_sorts_by_price(self):
        idx = R.Index(PRODUCTS)
        got = [idx.products[i]["p"] for i in idx.search("cheapest serum", 8)["idx"]]
        self.assertEqual(got, sorted(got))

    def test_price_relaxes_before_category_and_says_so(self):
        idx = R.Index(PRODUCTS)
        r = idx.search("lipstick under 100", 8)
        self.assertEqual(r["relaxed"], "price")
        self.assertEqual({idx.products[i]["c"] for i in r["idx"]}, {"Lipstick"})
        r2 = idx.search("blush", 8)
        self.assertEqual(r2["relaxed"], "category")

    def test_filters_can_be_switched_off_for_evaluation(self):
        idx = R.Index(PRODUCTS)
        r = idx.search("lipstick under 1000", 8, filters=False)
        self.assertEqual(r["filters"], {})

    def test_free_text_that_matches_nothing_returns_nothing(self):
        idx = R.Index(PRODUCTS)
        self.assertEqual(idx.search("quantum entanglement of unicorns", 5)["idx"], [])


class RetrievalTests(unittest.TestCase):
    def test_bm25_ranks_exact_ingredient_first(self):
        idx = R.Index(PRODUCTS)
        r = idx.search("niacinamide", 3)
        self.assertEqual(ids(idx, r)[0], "P1003")
        self.assertEqual(r["mode"], "bm25")

    def test_rrf_rewards_agreement(self):
        fused = R.rrf([[1, 2, 3], [3, 1, 4]])
        self.assertEqual(set(fused[:2]), {1, 3})
        self.assertIn(fused[-1], (2, 4))

    def test_dense_finds_what_keywords_cannot(self):
        q = "settle my angry cheeks"                   # none of these words appear in any product text
        bm = R.Index(PRODUCTS)
        hy = R.Index(PRODUCTS, fake_embed)
        self.assertEqual(bm.search(q, 3, facets=False)["idx"], [])
        r = hy.search(q, 3, facets=False)
        self.assertEqual(r["mode"], "hybrid")
        self.assertEqual(ids(hy, r)[0], "P1008")

    def test_facets_prefer_matching_skin_type_and_concern(self):
        idx = R.Index(PRODUCTS)
        top = ids(idx, idx.search("serum for oily skin with pimples", 3))
        self.assertEqual(top[0], "P1003")

    def test_embeddings_cached_to_disk(self):
        R.Index(PRODUCTS, fake_embed).search("shine", 2)
        self.assertTrue(any(R.CACHE_DIR.glob("emb_*.npy")))

    def test_embedding_failure_degrades_to_keywords_not_error(self):
        def boom(_):
            raise RuntimeError("api down")
        idx = R.Index(PRODUCTS, boom)
        r = idx.search("niacinamide", 3)
        self.assertEqual(r["mode"], "bm25")
        self.assertEqual(ids(idx, r)[0], "P1003")

    def test_blocked_products_never_retrieved_by_any_retriever(self):
        hy = R.Index(PRODUCTS, fake_embed)
        for q in ("niacinamide", "calm my angry cheeks", "serum", "lipstick under 2000", "oily skin"):
            got = set(ids(hy, hy.search(q, 8, {"P1003", "P1001", "P1005"})))
            self.assertFalse(got & {"P1003", "P1001", "P1005"}, q)

    def test_why_explains_the_match(self):
        idx = R.Index(PRODUCTS)
        q = R.Query("niacinamide serum for oily skin under 800")
        why = idx.why(idx.by_id["P1003"], q)
        self.assertIn("Serum", why)
        self.assertIn("Under Rs 800", why)
        self.assertIn("Suits oily skin", why)
        self.assertTrue(any(w.startswith("Contains") for w in why))


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
        r, _ = self.ask({"answer": "Clear Niacinamide Serum is good.", "product_ids": [], "needs_doctor": False}, text="niacinamide serum")
        self.assertEqual(r["product_ids"], ["P1003"])
        self.assertIn("[P1003]", r["answer"])

    def test_invented_or_unretrieved_tags_are_dropped(self):
        r, _ = self.ask({"answer": "Use [P1001] and [P9999].", "product_ids": ["P1001", "P9999"], "needs_doctor": False})
        self.assertEqual(r["product_ids"], ["P1001"])
        self.assertNotIn("P9999", r["answer"])

    def test_blocked_products_never_reach_the_model(self):
        r, llm = self.ask({"answer": "ok", "product_ids": [], "needs_doctor": False}, blocked_raw=["P1001", "bad id", 5])
        self.assertNotIn("P1001", llm.calls[0]["system"])
        self.assertNotIn("Zenith", llm.calls[0]["system"])
        self.assertNotIn("P1001", [x["id"] for x in r["results"]])

    def test_filters_are_applied_and_told_to_the_model_and_returned_to_the_page(self):
        r, llm = self.ask({"answer": "ok", "product_ids": [], "needs_doctor": False}, text="a pink lipstick under 1000")
        self.assertEqual([x["id"] for x in r["results"]], ["P1005"])
        self.assertEqual(r["filters"]["max_price"], 1000)
        self.assertEqual(r["total_matches"], 1)
        self.assertIn("category Lipstick", llm.calls[0]["system"])
        self.assertIn("price up to Rs 1000", llm.calls[0]["system"])
        self.assertIn("colour", llm.calls[0]["system"])   # the rule about unlisted properties such as shade

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
        self.assertEqual(r["retrieved"][0], "P1003")

    def test_needs_doctor_passes_through(self):
        r, _ = self.ask({"answer": "Please see a dermatologist.", "product_ids": [], "needs_doctor": True}, text="calm my angry cheeks")
        self.assertTrue(r["needs_doctor"])

    def test_model_failure_still_returns_the_search_results(self):
        def boom(**k):
            raise RuntimeError("x")
        llm = types.SimpleNamespace(messages=types.SimpleNamespace(create=boom))
        r = R.ask("lipsticks under 1000", client=llm, model="claude-sonnet-5-5", provider="anthropic", index=R.Index(PRODUCTS, fake_embed))
        self.assertFalse(r["ok"])
        self.assertTrue(r["reason"].startswith("api_error"))
        self.assertEqual([x["id"] for x in r["results"]], ["P1005"])     # the page can still show the matches without an AI sentence

    def test_everything_blocked_gives_honest_no_result(self):
        r = R.ask("sunscreen", blocked_raw=[p["id"] for p in PRODUCTS], index=R.Index(PRODUCTS, fake_embed))
        self.assertTrue(r["ok"])
        self.assertEqual(r["results"], [])
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
