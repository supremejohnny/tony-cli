from __future__ import annotations

from ..base import RuntimeCommand


class ExitCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /exit 已执行。退出当前 Tony REPL 会话。" + f" args={argument}"
        return "[real] /exit 已执行。退出当前 Tony REPL 会话。"


COMMAND = ExitCommand(
    name='exit',
    summary='退出当前 Tony REPL 会话。',
    source_hint='src/commands/runtime/exit/__init__.py',
)
