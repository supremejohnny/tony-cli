from __future__ import annotations

from ..base import RuntimeCommand


class DiffCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /diff 已执行。查看当前改动 diff 摘要。" + f" args={argument}"
        return "[real] /diff 已执行。查看当前改动 diff 摘要。"


COMMAND = DiffCommand(
    name='diff',
    summary='查看当前改动 diff 摘要。',
    source_hint='src/commands/runtime/diff/__init__.py',
)
