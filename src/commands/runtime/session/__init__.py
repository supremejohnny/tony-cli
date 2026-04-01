from __future__ import annotations

from ..base import RuntimeCommand


class SessionCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /session 已执行。查看当前 session 概况。" + f" args={argument}"
        return "[real] /session 已执行。查看当前 session 概况。"


COMMAND = SessionCommand(
    name='session',
    summary='查看当前 session 概况。',
    source_hint='src/commands/runtime/session/__init__.py',
)
