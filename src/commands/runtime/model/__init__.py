from __future__ import annotations

from ..base import RuntimeCommand


class ModelCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /model 已执行。用法: /model <name>" + f" args={argument}"
        return "[real] /model 已执行。用法: /model <name>"


COMMAND = ModelCommand(
    name='model',
    summary='切换默认模型。',
    source_hint='src/commands/runtime/model/__init__.py',
)
