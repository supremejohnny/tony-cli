from __future__ import annotations

from ..base import RuntimeCommand


class CommitCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /commit 已执行。提交当前仓库改动。" + f" args={argument}"
        return "[real] /commit 已执行。提交当前仓库改动。"


COMMAND = CommitCommand(
    name='commit',
    summary='提交当前仓库改动。',
    source_hint='src/commands/runtime/commit/__init__.py',
)
