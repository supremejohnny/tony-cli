from __future__ import annotations

from ..base import RuntimeCommand


class ContextCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /context 已执行。查看当前上下文摘要。" + f" args={argument}"
        return "[real] /context 已执行。查看当前上下文摘要。"


COMMAND = ContextCommand(
    name='context',
    summary='查看当前上下文摘要。',
    source_hint='src/commands/runtime/context/__init__.py',
)
