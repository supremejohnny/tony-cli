from __future__ import annotations

from ..base import RuntimeCommand


class BranchCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /branch 已执行。查看或切换分支。" + f" args={argument}"
        return "[real] /branch 已执行。查看或切换分支。"


COMMAND = BranchCommand(
    name='branch',
    summary='查看或切换分支。',
    source_hint='src/commands/runtime/branch/__init__.py',
)
