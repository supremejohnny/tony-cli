from __future__ import annotations

from ..base import RuntimeCommand


class ResumeCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /resume 已执行。用法: /resume <session_id>" + f" args={argument}"
        return "[real] /resume 已执行。用法: /resume <session_id>"


COMMAND = ResumeCommand(
    name='resume',
    summary='恢复历史 session。',
    source_hint='src/commands/runtime/resume/__init__.py',
)
