from __future__ import annotations

import os
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...
    def generate_vision(
        self,
        system_prompt: str,
        image_blocks: list[dict],
        text_prompt: str,
    ) -> str: ...


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

    def generate_vision(
        self,
        system_prompt: str,
        image_blocks: list[dict],
        text_prompt: str,
    ) -> str:
        from tony.api_client import MessageRequest  # type: ignore[import]
        from tony.models import TextBlock  # type: ignore[import]

        content: list[dict] = image_blocks + [{"type": "text", "text": text_prompt}]
        req = MessageRequest(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": content}],
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

_MOCK_DISTILL_JSON = """{
  "version": "1.0",
  "source": {
    "file_name": "mock_lecture.pptx",
    "file_hash": "",
    "distilled_at": ""
  },
  "global_summary": "A mock lecture covering paging and the Translation Lookaside Buffer (TLB). Introduces virtual-to-physical address mapping and explains how the TLB accelerates translation.",
  "main_topics": ["paging", "address translation", "TLB", "virtual memory"],
  "chunks": [
    {
      "chunk_id": "chunk_01",
      "slide_range": [1, 2],
      "titles": ["Overview", "Paging Basics"],
      "summary_short": "Introduces paging as a fixed-size memory management scheme and the page table used for address translation.",
      "key_points": [
        "Virtual memory is divided into fixed-size pages.",
        "Physical memory is divided into frames of the same size.",
        "The page table maps virtual page numbers to physical frame numbers."
      ],
      "definitions": [
        {"term": "paging", "definition": "A memory management scheme that divides virtual memory into fixed-size pages and physical memory into fixed-size frames."},
        {"term": "page table", "definition": "A data structure that maps virtual page numbers to physical frame numbers."}
      ],
      "entities": ["paging", "page table", "virtual memory", "frame"],
      "question_signatures": [
        "What is paging?",
        "How does address translation work in paging?",
        "What is a page table?"
      ],
      "keywords": ["paging", "page table", "frame", "virtual address", "physical address"],
      "anchors": {
        "start_slide": 1,
        "end_slide": 2,
        "prev_title": null,
        "next_title": "Translation Lookaside Buffer"
      }
    },
    {
      "chunk_id": "chunk_02",
      "slide_range": [3, 4],
      "titles": ["Translation Lookaside Buffer", "TLB Example"],
      "summary_short": "Explains the TLB as a cache for recent page table translations and illustrates hit vs miss latency.",
      "key_points": [
        "The TLB caches recent page table entries in hardware.",
        "A TLB hit avoids a slow page table memory lookup.",
        "A TLB miss falls back to the full page table at the cost of one extra memory access."
      ],
      "definitions": [
        {"term": "TLB", "definition": "A small hardware cache storing recent virtual-to-physical page table translations."}
      ],
      "entities": ["TLB", "page table", "TLB hit", "TLB miss"],
      "question_signatures": [
        "What is a TLB?",
        "Why does a TLB improve performance?",
        "What happens on a TLB miss?"
      ],
      "keywords": ["TLB", "translation lookaside buffer", "TLB hit", "TLB miss", "cache"],
      "anchors": {
        "start_slide": 3,
        "end_slide": 4,
        "prev_title": "Paging Basics",
        "next_title": null
      }
    }
  ]
}"""


_MOCK_VISION_RESPONSE = (
    "[Visual: A diagram showing example content with labeled nodes and connecting arrows. (mock)]"
)


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
        if "knowledge distiller" in sp:
            return _MOCK_DISTILL_JSON
        # Layer 1 responses
        combined = (system_prompt + user_prompt).lower()
        if "spec" in combined and "slides" in combined and "audience" in combined:
            return _MOCK_SPEC_JSON
        return _MOCK_PLAN_JSON

    def generate_vision(
        self,
        system_prompt: str,
        image_blocks: list[dict],
        text_prompt: str,
    ) -> str:
        return _MOCK_VISION_RESPONSE


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
