from __future__ import annotations

from ..base import RuntimeCommand


class UsageCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /usage 已执行。查看 usage 统计。" + f" args={argument}"
        return "[real] /usage 已执行。查看 usage 统计。"


COMMAND = UsageCommand(
    name='usage',
    summary='查看 usage 统计。',
    source_hint='src/commands/runtime/usage/__init__.py',
)
