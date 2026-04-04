from __future__ import annotations

import os
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


# ---------------------------------------------------------------------------
# Real Anthropic client (wraps tony's AnthropicClient)
# ---------------------------------------------------------------------------

class AnthropicLLMClient:
    """Simple prompt→text wrapper around tony's AnthropicClient.

    Uses send_message() (non-streaming) — powergen only needs a single
    response per call, not a tool-use loop.
    """

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        from tony.api_client import AnthropicClient  # type: ignore[import]
        self._client = AnthropicClient(model=model)
        self._model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        from tony.api_client import MessageRequest  # type: ignore[import]
        from tony.models import TextBlock  # type: ignore[import]

        req = MessageRequest(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": user_prompt}],
            system=[{"type": "text", "text": system_prompt}],
            stream=False,
        )
        resp = self._client.send_message(req)
        for block in resp.content:
            if isinstance(block, TextBlock):
                return block.text
        return ""

    def close(self) -> None:
        self._client.close()


# ---------------------------------------------------------------------------
# Mock client (offline testing)
# ---------------------------------------------------------------------------

_MOCK_PLAN_JSON = """{
  "overview": "A 5-slide introduction to AI-powered development tools.",
  "slide_summaries": [
    "Title slide: The Future of AI Development",
    "Problem: Developer productivity bottlenecks today",
    "Solution: AI pair programming and automation",
    "Demo: Live examples with tony and powergen",
    "Call to action: Getting started today"
  ],
  "references": [],
  "open_questions": ["Should we include benchmark data?"]
}"""

_MOCK_SPEC_JSON = """{
  "title": "The Future of AI Development",
  "audience": "Software engineers and tech leads",
  "tone": "professional",
  "theme_reference": "",
  "slides": [
    {
      "index": 0,
      "title": "The Future of AI Development",
      "bullets": [],
      "layout": "Title Slide",
      "notes": "Welcome the audience and introduce the topic."
    },
    {
      "index": 1,
      "title": "Developer Productivity Bottlenecks",
      "bullets": [
        "Context switching costs 40% of focus time",
        "Repetitive boilerplate slows delivery",
        "Code review backlogs accumulate"
      ],
      "layout": "Title and Content",
      "notes": "Open with pain points the audience recognises."
    },
    {
      "index": 2,
      "title": "AI Pair Programming & Automation",
      "bullets": [
        "LLM agents handle repetitive coding tasks",
        "Natural language → working code",
        "Continuous context awareness"
      ],
      "layout": "Title and Content",
      "notes": "Transition from problem to solution."
    },
    {
      "index": 3,
      "title": "Live Demo: tony & powergen",
      "bullets": [
        "tony: AI agent CLI for code tasks",
        "powergen: AI presentation generator",
        "Both built on Anthropic Claude"
      ],
      "layout": "Title and Content",
      "notes": "Show a quick demo if time allows."
    },
    {
      "index": 4,
      "title": "Get Started Today",
      "bullets": [
        "pip install tony-cli",
        "Set ANTHROPIC_API_KEY",
        "Run: tony / powergen"
      ],
      "layout": "Title and Content",
      "notes": "End with a clear call to action."
    }
  ]
}"""


class MockLLMClient:
    """Returns canned responses for offline / CI testing."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        combined = (system_prompt + user_prompt).lower()
        if "spec" in combined and "slides" in combined and "audience" in combined:
            return _MOCK_SPEC_JSON
        return _MOCK_PLAN_JSON


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_llm_client(mock: bool = False, model: str = "claude-sonnet-4-6") -> LLMClient:
    """Return a MockLLMClient or AnthropicLLMClient.

    Priority: explicit mock flag > POWERGEN_USE_MOCK env var > real client.
    """
    if mock or os.environ.get("POWERGEN_USE_MOCK") == "1":
        return MockLLMClient()
    return AnthropicLLMClient(model=model)
