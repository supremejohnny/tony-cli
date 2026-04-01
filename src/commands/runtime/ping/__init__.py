from __future__ import annotations

from ..base import RuntimeCommand


class PingCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        return 'pong'


COMMAND = PingCommand(
    name='ping',
    summary='健康检查命令。',
    source_hint='src/commands/runtime/ping/__init__.py',
)
