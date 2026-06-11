"""Unit tests for the amplification engine (Reddit reply -> X thread / LinkedIn)."""

import pytest

from app.services.product.amplify import (
    LINKEDIN_MAX_CHARS,
    SOURCE_CLOSE,
    SOURCE_OPEN,
    TWEET_MAX_CHARS,
    amplify_to_linkedin,
    amplify_to_x_thread,
)


class FakeLLM:
    """Injectable LLM stub that returns queued responses and records calls."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def call_json(self, system_prompt, user_content, temperature=0.2):
        self.calls.append({"system": system_prompt, "user": user_content})
        if not self._responses:
            return None
        return self._responses.pop(0)


SOURCE = {
    "title": "How do I automate my reporting?",
    "body": "We waste hours every week on manual spreadsheets.",
    "subreddit": "dataengineering",
    "content": "We had the same problem. We fixed it with three small workflow changes...",
}

BRAND = {"brand_name": "RedditFlow", "summary": "Find Reddit opportunities", "voice_notes": "helpful"}


# ── X thread generation ───────────────────────────────────────────────


def test_x_thread_valid_response():
    tweets = ["Hook tweet about reporting.", "Second tweet with details.", "Third tweet with the CTA."]
    llm = FakeLLM([{"tweets": tweets}])

    result = amplify_to_x_thread(SOURCE, BRAND, llm=llm)

    assert result == tweets
    assert len(llm.calls) == 1  # no re-prompt needed
    assert all(len(t) <= TWEET_MAX_CHARS for t in result)


def test_x_thread_over_280_reprompts_once_and_uses_fixed_version():
    long_tweet = "x" * 300
    fixed = ["Short hook.", "Short middle.", "Short close."]
    llm = FakeLLM([
        {"tweets": [long_tweet, "ok tweet", "another ok"]},
        {"tweets": fixed},
    ])

    result = amplify_to_x_thread(SOURCE, BRAND, llm=llm)

    assert result == fixed
    assert len(llm.calls) == 2
    # The re-prompt must point out the violation
    retry_prompt = llm.calls[1]["user"]
    assert "280" in retry_prompt
    assert "300 characters" in retry_prompt


def test_x_thread_still_over_after_reprompt_hard_truncates():
    long_tweet = "y" * 320
    llm = FakeLLM([
        {"tweets": [long_tweet, "fine"]},
        {"tweets": [long_tweet, "fine"]},  # still violating
    ])

    result = amplify_to_x_thread(SOURCE, BRAND, llm=llm)

    assert len(llm.calls) == 2
    assert result[0] == "y" * 277 + "…"
    assert len(result[0]) == 278
    assert result[1] == "fine"


def test_x_thread_reprompt_failure_truncates_first_response():
    long_tweet = "z" * 290
    llm = FakeLLM([{"tweets": [long_tweet, "ok"]}])  # retry returns None

    result = amplify_to_x_thread(SOURCE, BRAND, llm=llm)

    assert result[0] == "z" * 277 + "…"
    assert result[1] == "ok"


def test_x_thread_llm_none_raises_runtime_error():
    llm = FakeLLM([None])
    with pytest.raises(RuntimeError):
        amplify_to_x_thread(SOURCE, BRAND, llm=llm)


def test_x_thread_empty_tweets_raises_runtime_error():
    llm = FakeLLM([{"tweets": []}])
    with pytest.raises(RuntimeError):
        amplify_to_x_thread(SOURCE, BRAND, llm=llm)


def test_x_thread_accepts_bare_list_payload():
    llm = FakeLLM([["tweet one", "tweet two"]])
    assert amplify_to_x_thread(SOURCE, BRAND, llm=llm) == ["tweet one", "tweet two"]


# ── Injection-safety delimiters ───────────────────────────────────────


def test_source_content_wrapped_in_data_only_delimiters_for_x():
    llm = FakeLLM([{"tweets": ["a", "b", "c"]}])
    amplify_to_x_thread(SOURCE, BRAND, llm=llm)

    user = llm.calls[0]["user"]
    assert SOURCE_OPEN in user
    assert SOURCE_CLOSE in user
    # Source content sits between the delimiters
    inner = user.split(SOURCE_OPEN)[1].split(SOURCE_CLOSE)[0]
    assert SOURCE["title"] in inner
    assert SOURCE["content"] in inner
    assert "data only" in llm.calls[0]["system"].lower()


def test_source_content_wrapped_in_data_only_delimiters_for_linkedin():
    llm = FakeLLM([{"content": "p" * 1500}])
    amplify_to_linkedin(SOURCE, BRAND, llm=llm)

    user = llm.calls[0]["user"]
    assert SOURCE_OPEN in user
    assert SOURCE_CLOSE in user


# ── Voice profile handling ────────────────────────────────────────────


def test_voice_profile_style_guide_and_banned_phrases_in_system_prompt():
    voice = {"style_guide": "Write like a friendly pirate.", "banned_phrases": ["game changer", "synergy"]}
    llm = FakeLLM([{"tweets": ["a", "b", "c"]}])

    amplify_to_x_thread(SOURCE, BRAND, voice_profile=voice, llm=llm)

    system = llm.calls[0]["system"]
    assert "Write like a friendly pirate." in system
    assert "game changer" in system
    assert "synergy" in system


def test_voice_profile_applies_to_linkedin_too():
    voice = {"style_guide": "Direct and data-driven.", "banned_phrases": ["thought leader"]}
    llm = FakeLLM([{"content": "q" * 1400}])

    amplify_to_linkedin(SOURCE, BRAND, voice_profile=voice, llm=llm)

    system = llm.calls[0]["system"]
    assert "Direct and data-driven." in system
    assert "thought leader" in system


# ── LinkedIn length validation ────────────────────────────────────────


def test_linkedin_valid_length_returned_as_is():
    content = "L" * 2000
    llm = FakeLLM([{"content": content}])

    assert amplify_to_linkedin(SOURCE, BRAND, llm=llm) == content
    assert len(llm.calls) == 1


def test_linkedin_over_3000_reprompts_then_uses_fixed_version():
    too_long = "A" * 3500
    fixed = "B" * 1500
    llm = FakeLLM([{"content": too_long}, {"content": fixed}])

    result = amplify_to_linkedin(SOURCE, BRAND, llm=llm)

    assert result == fixed
    assert len(llm.calls) == 2
    assert "3000" in llm.calls[1]["user"]


def test_linkedin_still_over_truncates_at_paragraph_boundary():
    para_a = "A" * 1500
    para_b = "B" * 1400
    para_c = "C" * 500
    too_long = f"{para_a}\n\n{para_b}\n\n{para_c}"
    llm = FakeLLM([{"content": too_long}, {"content": too_long}])

    result = amplify_to_linkedin(SOURCE, BRAND, llm=llm)

    assert result == f"{para_a}\n\n{para_b}"
    assert len(result) <= LINKEDIN_MAX_CHARS


def test_linkedin_single_huge_paragraph_hard_slices():
    too_long = "X" * 3500
    llm = FakeLLM([{"content": too_long}, {"content": too_long}])

    result = amplify_to_linkedin(SOURCE, BRAND, llm=llm)

    assert len(result) == LINKEDIN_MAX_CHARS


def test_linkedin_llm_none_raises_runtime_error():
    llm = FakeLLM([None])
    with pytest.raises(RuntimeError):
        amplify_to_linkedin(SOURCE, BRAND, llm=llm)


def test_linkedin_empty_content_raises_runtime_error():
    llm = FakeLLM([{"content": ""}])
    with pytest.raises(RuntimeError):
        amplify_to_linkedin(SOURCE, BRAND, llm=llm)
