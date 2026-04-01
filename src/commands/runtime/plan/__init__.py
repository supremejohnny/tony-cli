from __future__ import annotations

from ..base import RuntimeCommand


class PlanCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /plan 已执行。生成任务计划。" + f" args={argument}"
        return "[real] /plan 已执行。生成任务计划。"


COMMAND = PlanCommand(
    name='plan',
    summary='生成任务计划。',
    source_hint='src/commands/runtime/plan/__init__.py',
)
