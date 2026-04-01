from __future__ import annotations

from ..base import RuntimeCommand


class InitCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /init 已执行。初始化当前工作区。" + f" args={argument}"
        return "[real] /init 已执行。初始化当前工作区。"


COMMAND = InitCommand(
    name='init',
    summary='初始化当前工作区。',
    source_hint='src/commands/runtime/init/__init__.py',
)
