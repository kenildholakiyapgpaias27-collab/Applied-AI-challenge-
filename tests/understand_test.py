#!/usr/bin/env python3
"""Tests for the chat/voice meaning layer (backend/understand_service.py) with a fake Claude client.

No API key or network needed:
    python3 tests/understand_test.py
"""
import json
import os
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import understand_service as U  # noqa: E402

VOCAB = {
    "concerns": {
        "acne": {"label": "Breakouts and acne", "options": ["Small pimples now and then", "Blackheads and whiteheads", "Red, inflamed spots"]},
        "dullness": {"label": "Dull, tired skin", "options": ["Tired, flat-looking skin", "Rough texture"]},
        "sunscreen": {"label": "Sunscreen", "options": []},
    },
    "reactions": ["salicylic acid", "vitamin c"],
}


def block(text):
    return types.SimpleNamespace(type="text", text=text)


class FakeAPIError(Exception):
    def __init__(self, status):
        super().__init__("boom")
        self.status_code = status


class FakeClient:
    """Mimics client.messages.create and client.beta.messages.create."""

    def __init__(self, payload=None, stop_reason="end_turn", beta_error=None, error=None):
        self.payload, self.stop_reason, self.beta_error, self.error = payload, stop_reason, beta_error, error
        self.calls = []
        self.messages = types.SimpleNamespace(create=self._create)
        self.beta = types.SimpleNamespace(messages=types.SimpleNamespace(create=self._beta_create))

    def _resp(self):
        body = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return types.SimpleNamespace(content=[block(body)], stop_reason=self.stop_reason)

    def _create(self, **kw):
        self.calls.append(("plain", kw))
        if self.error:
            raise self.error
        return self._resp()

    def _beta_create(self, **kw):
        self.calls.append(("beta", kw))
        if self.beta_error:
            raise self.beta_error
        if self.error:
            raise self.error
        return self._resp()


def good(**over):
    base = {
        "on_topic": True, "escalate": False, "goal": "routine", "gender": None,
        "concerns": ["acne"], "follow_ups": [{"concern": "acne", "option": 1}], "skin": "oily",
        "city": "Pune", "budget_inr": 800, "sensitive_skin": None, "avoid_fragrance": True,
        "avoid_essential_oils": None, "pregnancy": None, "reactions": ["salicylic acid"],
        "understood": "You have oily skin with blackheads, live in Pune, and want to spend under 800.",
    }
    base.update(over)
    return base


class SchemaTests(unittest.TestCase):
    def test_schema_is_strict_and_uses_app_vocabulary(self):
        sch = U.build_schema(U.clean_vocab(VOCAB))
        self.assertIs(sch["additionalProperties"], False)
        self.assertEqual(set(sch["required"]), set(sch["properties"]))   # every field required, "unknown" is an explicit null
        self.assertEqual(sch["properties"]["concerns"]["items"]["enum"], ["acne", "dullness", "sunscreen"])
        self.assertEqual(sch["properties"]["reactions"]["items"]["enum"], ["salicylic acid", "vitamin c"])
        self.assertIs(sch["properties"]["follow_ups"]["items"]["additionalProperties"], False)

    def test_skin_tone_is_never_extractable(self):
        keys = set(U.build_schema(U.clean_vocab(VOCAB))["properties"])
        self.assertFalse({"tone", "undertone", "skin_tone", "monk"} & keys)

    def test_prompt_lists_follow_up_options_and_warns_about_injection(self):
        p = U.build_system(U.clean_vocab(VOCAB))
        self.assertIn("follow-up option 1: Blackheads and whiteheads", p)
        self.assertIn("untrusted data", p)


class VocabTests(unittest.TestCase):
    def test_rejects_malformed_vocab(self):
        for bad in (None, [], {}, {"concerns": {}, "reactions": []}, {"concerns": {"a": 1}, "reactions": []},
                    {"concerns": {"a": {"label": "x" * 500}}, "reactions": []},
                    {"concerns": {"a": {"label": "x", "options": ["o"] * 40}}, "reactions": []},
                    {"concerns": {"a": {"label": "x"}}, "reactions": "no"}):
            with self.assertRaises(U.VocabError):
                U.clean_vocab(bad)


class UnderstandTests(unittest.TestCase):
    def run_it(self, client, text="my face is oily and I get blackheads, in Pune, under 800 rupees"):
        return U.understand(text, VOCAB, client=client, model="claude-sonnet-5-5")

    def test_happy_path(self):
        c = FakeClient(good())
        r = self.run_it(c)
        self.assertTrue(r["ok"])
        s = r["slots"]
        self.assertEqual((s["goal"], s["skin"], s["city"], s["budget_inr"]), ("routine", "oily", "Pune", 800))
        self.assertEqual(s["follow_ups"], {"acne": 1})
        self.assertEqual(s["reactions"], ["salicylic acid"])
        kw = c.calls[0][1]
        self.assertEqual(kw["output_config"]["format"]["type"], "json_schema")   # structured output, not free text
        self.assertEqual(kw["messages"][0]["content"], "my face is oily and I get blackheads, in Pune, under 800 rupees")

    def test_out_of_vocabulary_and_bad_values_are_dropped(self):
        r = self.run_it(FakeClient(good(
            concerns=["acne", "made_up", "acne", "dullness", "sunscreen"], goal="teleport", gender="robot", skin="purple",
            follow_ups=[{"concern": "acne", "option": 9}, {"concern": "dullness", "option": 1}, {"concern": "ghost", "option": 0},
                        {"concern": "sunscreen", "option": 0}],
            budget_inr=5, reactions=["salicylic acid", "bleach"], city="  ", pregnancy="yes please")))
        s = r["slots"]
        self.assertEqual(s["concerns"], ["acne", "dullness", "sunscreen"])   # de-duplicated, unknown removed, capped at 3
        self.assertEqual(s["follow_ups"], {"dullness": 1})                   # index 9 / unknown concern / option-less concern removed
        self.assertIsNone(s["goal"])
        self.assertIsNone(s["gender"])
        self.assertIsNone(s["skin"])
        self.assertIsNone(s["budget_inr"])
        self.assertIsNone(s["city"])
        self.assertIsNone(s["pregnancy"])
        self.assertEqual(s["reactions"], ["salicylic acid"])

    def test_goal_questions_can_be_answered_through_follow_ups(self):
        vocab = {"concerns": {"sunscreen": {"label": "Sunscreen", "options": ["Daily commute", "Long hours outdoors"]}}, "reactions": []}
        c = FakeClient(good(concerns=[], follow_ups=[{"concern": "sunscreen", "option": 1}], goal="sunscreen", reactions=[]))
        s = U.understand("beach holiday", vocab, client=c, model="claude-sonnet-5-5")["slots"]
        self.assertEqual(s["follow_ups"], {"sunscreen": 1})
        self.assertEqual(s["concerns"], [])

    def test_pregnancy_mapping_never_assumes(self):
        self.assertIs(self.run_it(FakeClient(good(pregnancy="pregnant_or_nursing")))["slots"]["pregnancy"], True)
        self.assertIs(self.run_it(FakeClient(good(pregnancy="not_pregnant")))["slots"]["pregnancy"], False)
        self.assertIsNone(self.run_it(FakeClient(good(pregnancy=None)))["slots"]["pregnancy"])

    def test_escalate_and_off_topic_pass_through(self):
        s = self.run_it(FakeClient(good(escalate=True, on_topic=False)))["slots"]
        self.assertTrue(s["escalate"])
        self.assertFalse(s["on_topic"])

    def test_failures_become_ok_false_not_exceptions(self):
        self.assertEqual(self.run_it(FakeClient(good(), stop_reason="refusal"))["reason"], "refusal")
        self.assertEqual(self.run_it(FakeClient("not json"))["reason"], "bad_json")
        self.assertEqual(self.run_it(FakeClient("[1,2]"))["reason"], "bad_json")
        self.assertTrue(self.run_it(FakeClient(error=FakeAPIError(529)))["reason"].startswith("api_error"))
        self.assertEqual(U.understand("", VOCAB, client=FakeClient(good()))["reason"], "empty")
        self.assertTrue(U.understand("hi", {"nope": 1}, client=FakeClient(good()))["reason"].startswith("bad_vocab"))

    def test_disabled_without_key(self):
        old = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            self.assertEqual(U.understand("oily skin", VOCAB)["reason"], "disabled")
            self.assertFalse(U.llm_enabled())
        finally:
            if old is not None:
                os.environ["ANTHROPIC_API_KEY"] = old

    def test_text_is_capped(self):
        c = FakeClient(good())
        U.understand("a" * 5000, VOCAB, client=c, model="claude-sonnet-5-5")
        self.assertEqual(len(c.calls[0][1]["messages"][0]["content"]), U.MAX_TEXT)

    def test_opus_uses_fallbacks_and_retries_plain_if_beta_shape_rejected(self):
        c = FakeClient(good())
        U.understand("oily skin", VOCAB, client=c, model="claude-opus-5-5")
        self.assertEqual(c.calls[0][0], "beta")
        self.assertEqual(c.calls[0][1]["fallbacks"], "default")
        c2 = FakeClient(good(), beta_error=FakeAPIError(400))
        self.assertTrue(U.understand("oily skin", VOCAB, client=c2, model="claude-opus-5-5")["ok"])
        self.assertEqual([k for k, _ in c2.calls], ["beta", "plain"])
        c3 = FakeClient(good(), beta_error=FakeAPIError(500))   # a real outage is not retried as "plain"
        self.assertFalse(U.understand("oily skin", VOCAB, client=c3, model="claude-opus-5-5")["ok"])


class FakeOpenAI:
    """Mimics client.chat.completions.create."""

    def __init__(self, payload=None, refusal=None, finish="stop", error=None):
        self.payload, self.refusal, self.finish, self.error, self.calls = payload, refusal, finish, error, []
        self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        if self.error:
            raise self.error
        msg = types.SimpleNamespace(content=json.dumps(self.payload), refusal=self.refusal)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg, finish_reason=self.finish)])


class OpenAIProviderTests(unittest.TestCase):
    def test_openai_happy_path_uses_strict_schema(self):
        c = FakeOpenAI(good())
        r = U.understand("oily skin", VOCAB, client=c, provider="openai", model="gpt-test")
        self.assertTrue(r["ok"])
        self.assertEqual(r["slots"]["city"], "Pune")
        kw = c.calls[0]
        self.assertEqual(kw["model"], "gpt-test")
        rf = kw["response_format"]
        self.assertEqual(rf["type"], "json_schema")
        self.assertIs(rf["json_schema"]["strict"], True)
        self.assertEqual(kw["messages"][0]["role"], "system")
        self.assertEqual(kw["messages"][1], {"role": "user", "content": "oily skin"})

    def test_openai_refusal_and_errors_fall_back(self):
        self.assertEqual(U.understand("x", VOCAB, client=FakeOpenAI(good(), refusal="no"), provider="openai")["reason"], "refusal")
        self.assertEqual(U.understand("x", VOCAB, client=FakeOpenAI(good(), finish="content_filter"), provider="openai")["reason"], "refusal")
        self.assertTrue(U.understand("x", VOCAB, client=FakeOpenAI(error=FakeAPIError(429)), provider="openai")["reason"].startswith("api_error"))

    def test_provider_choice_from_environment(self):
        keys = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AAINA_LLM_PROVIDER")
        old = {k: os.environ.pop(k, None) for k in keys}
        try:
            self.assertIsNone(U._provider())
            os.environ["OPENAI_API_KEY"] = "x"
            self.assertEqual(U._provider(), "openai")
            self.assertTrue(U.llm_enabled())
            os.environ["ANTHROPIC_API_KEY"] = "y"
            self.assertEqual(U._provider(), "anthropic")              # Anthropic wins when both are set...
            os.environ["AAINA_LLM_PROVIDER"] = "openai"
            self.assertEqual(U._provider(), "openai")                 # ...unless forced
            del os.environ["OPENAI_API_KEY"]
            self.assertIsNone(U._provider())                          # forced provider with no key: off, never a silent switch
        finally:
            for k, v in old.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v


class RouteTests(unittest.TestCase):
    def test_route_and_rate_limit(self):
        try:
            from fastapi.testclient import TestClient
            from backend import app as appmod
        except Exception as e:  # fastapi/httpx not installed in this environment
            self.skipTest("fastapi test client unavailable: %s" % e)
        old = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            tc = TestClient(appmod.app)
            self.assertEqual(tc.get("/api/understand/status").json(), {"enabled": False, "rag": None})
            r = tc.post("/api/understand", json={"text": "oily skin", "vocab": VOCAB})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json(), {"ok": False, "reason": "disabled"})
            self.assertEqual(tc.post("/api/understand", json={"text": "x"}).status_code, 422)   # vocab is required
            appmod._UNDERSTAND_HITS.clear()
            res = [tc.post("/api/understand", json={"text": "oily", "vocab": VOCAB}).json().get("reason") for _ in range(22)]
            self.assertEqual(res[-1], "rate_limited")
            appmod._UNDERSTAND_HITS.clear()
        finally:
            if old is not None:
                os.environ["ANTHROPIC_API_KEY"] = old


if __name__ == "__main__":
    unittest.main(verbosity=2)
