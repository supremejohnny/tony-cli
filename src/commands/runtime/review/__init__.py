from __future__ import annotations

from ..base import RuntimeCommand


class ReviewCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /review 已执行。触发代码审查工作流。" + f" args={argument}"
        return "[real] /review 已执行。触发代码审查工作流。"


COMMAND = ReviewCommand(
    name='review',
    summary='触发代码审查工作流。',
    source_hint='src/commands/runtime/review/__init__.py',
)
