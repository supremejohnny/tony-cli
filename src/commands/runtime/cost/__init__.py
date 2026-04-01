from __future__ import annotations

from ..base import RuntimeCommand


class CostCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /cost 已执行。查看 token 成本统计。" + f" args={argument}"
        return "[real] /cost 已执行。查看 token 成本统计。"


COMMAND = CostCommand(
    name='cost',
    summary='查看 token 成本统计。',
    source_hint='src/commands/runtime/cost/__init__.py',
)
