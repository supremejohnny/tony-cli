from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeCommand:
    name: str
    summary: str
    source_hint: str

    def execute(self, prompt: str) -> str:
        raise NotImplementedError
