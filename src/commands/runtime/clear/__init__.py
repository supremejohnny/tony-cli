from __future__ import annotations

from ..base import RuntimeCommand


class ClearCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /clear 已执行。清屏并保持会话。" + f" args={argument}"
        return "[real] /clear 已执行。清屏并保持会话。"


COMMAND = ClearCommand(
    name='clear',
    summary='清屏并保持会话。',
    source_hint='src/commands/runtime/clear/__init__.py',
)
