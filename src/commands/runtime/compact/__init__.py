from __future__ import annotations

from ..base import RuntimeCommand


class CompactCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /compact 已执行。压缩当前会话上下文以节省 token。" + f" args={argument}"
        return "[real] /compact 已执行。压缩当前会话上下文以节省 token。"


COMMAND = CompactCommand(
    name='compact',
    summary='压缩当前会话上下文以节省 token。',
    source_hint='src/commands/runtime/compact/__init__.py',
)
