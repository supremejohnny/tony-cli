from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union


# ---------------------------------------------------------------------------
# Content blocks
# ---------------------------------------------------------------------------

@dataclass
class TextBlock:
    text: str
    type: str = "text"


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict
    type: str = "tool_use"


@dataclass
class ToolResultBlock:
    tool_use_id: str
    content: str
    type: str = "tool_result"


ContentBlock = Union[TextBlock, ToolUseBlock, ToolResultBlock]


# ---------------------------------------------------------------------------
# Conversation message
# ---------------------------------------------------------------------------

@dataclass
class ConversationMessage:
    role: str  # "user" | "assistant" | "tool"
    blocks: list[ContentBlock]

    def to_dict(self) -> dict:
        blocks_out = []
        for b in self.blocks:
            if isinstance(b, TextBlock):
                blocks_out.append({"type": "text", "text": b.text})
            elif isinstance(b, ToolUseBlock):
                blocks_out.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
            elif isinstance(b, ToolResultBlock):
                blocks_out.append({"type": "tool_result", "tool_use_id": b.tool_use_id, "content": b.content})
        return {"role": self.role, "blocks": blocks_out}

    @classmethod
    def from_dict(cls, d: dict) -> "ConversationMessage":
        blocks: list[ContentBlock] = []
        for b in d.get("blocks", []):
            t = b.get("type")
            if t == "text":
                blocks.append(TextBlock(text=b["text"]))
            elif t == "tool_use":
                blocks.append(ToolUseBlock(id=b["id"], name=b["name"], input=b["input"]))
            elif t == "tool_result":
                blocks.append(ToolResultBlock(tool_use_id=b["tool_use_id"], content=b["content"]))
        return cls(role=d["role"], blocks=blocks)


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

@dataclass
class Session:
    messages: list[ConversationMessage] = field(default_factory=list)

    def save(self, path: str | Path) -> None:
        data = {"messages": [m.to_dict() for m in self.messages]}
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Session":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        messages = [ConversationMessage.from_dict(m) for m in data.get("messages", [])]
        return cls(messages=messages)


# ---------------------------------------------------------------------------
# Token usage
# ---------------------------------------------------------------------------

@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
        )


@dataclass
class UsageTracker:
    total: TokenUsage = field(default_factory=TokenUsage)

    def add(self, usage: TokenUsage) -> None:
        self.total = self.total + usage
