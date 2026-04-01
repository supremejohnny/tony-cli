from __future__ import annotations

from ..base import RuntimeCommand


class HooksCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /hooks 已执行。查看生命周期 hooks 状态。" + f" args={argument}"
        return "[real] /hooks 已执行。查看生命周期 hooks 状态。"


COMMAND = HooksCommand(
    name='hooks',
    summary='查看生命周期 hooks 状态。',
    source_hint='src/commands/runtime/hooks/__init__.py',
)
