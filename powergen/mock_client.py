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
            max_tokens=8192,
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


_MOCK_TEMPLATE_ANALYSIS_JSON = """{
  "slides": [
    {
      "slide_index": 1,
      "slide_relevant": true,
      "text_nodes": [
        {"original_text": "Presentation Title", "purpose": "title"},
        {"original_text": "Subtitle or tagline here", "purpose": "body"}
      ]
    },
    {
      "slide_index": 2,
      "slide_relevant": false,
      "text_nodes": [
        {"original_text": "How to use this template", "purpose": "title"},
        {"original_text": "Replace slide 1 with your topic title", "purpose": "bullet"},
        {"original_text": "Delete this instructions slide before presenting", "purpose": "bullet"}
      ]
    },
    {
      "slide_index": 3,
      "slide_relevant": true,
      "text_nodes": [
        {"original_text": "Slide Heading", "purpose": "title"},
        {"original_text": "First bullet point", "purpose": "bullet"},
        {"original_text": "Second bullet point", "purpose": "bullet"},
        {"original_text": "Third bullet point", "purpose": "bullet"}
      ]
    }
  ]
}"""

_MOCK_TEMPLATE_MAPPING_JSON = """{
  "mappings": [
    {"slide_index": 1, "original_text": "Presentation Title", "replacement_text": "Q1 Sales Review"},
    {"slide_index": 1, "original_text": "Subtitle or tagline here", "replacement_text": "APAC Region — January to March"},
    {"slide_index": 2, "original_text": "How to use this template", "replacement_text": "Instructions (should be skipped by filter)"},
    {"slide_index": 3, "original_text": "Slide Heading", "replacement_text": "Key Highlights"},
    {"slide_index": 3, "original_text": "First bullet point", "replacement_text": "Revenue up 12% YoY"},
    {"slide_index": 3, "original_text": "Second bullet point", "replacement_text": "New enterprise accounts: 8"},
    {"slide_index": 3, "original_text": "Third bullet point", "replacement_text": "Customer retention rate: 94%"}
  ]
}"""


class MockLLMClient:
    """Returns canned responses for offline / CI testing."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        # Use system_prompt only for Layer 2 detection: user_prompt for call 2
        # contains the full analysis JSON (with "text_nodes"), which would
        # cause a false match if we checked combined.
        sp = system_prompt.lower()
        if "presentation analyst" in sp:
            return _MOCK_TEMPLATE_ANALYSIS_JSON
        if "presentation writer" in sp:
            return _MOCK_TEMPLATE_MAPPING_JSON
        # Layer 1 responses
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
