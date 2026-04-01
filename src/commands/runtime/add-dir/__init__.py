from __future__ import annotations

from ..base import RuntimeCommand


class AddDirCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /add-dir 已执行。用法: /add-dir <path>" + f" args={argument}"
        return "[real] /add-dir 已执行。用法: /add-dir <path>"


COMMAND = AddDirCommand(
    name='add-dir',
    summary='将目录加入上下文。',
    source_hint='src/commands/runtime/add-dir/__init__.py',
)
