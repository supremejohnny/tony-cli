from __future__ import annotations

from ..base import RuntimeCommand


class MemoryCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /memory 已执行。管理持久化记忆入口。" + f" args={argument}"
        return "[real] /memory 已执行。管理持久化记忆入口。"


COMMAND = MemoryCommand(
    name='memory',
    summary='管理持久化记忆入口。',
    source_hint='src/commands/runtime/memory/__init__.py',
)
