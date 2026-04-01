from __future__ import annotations

from ..base import RuntimeCommand


class ConfigCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /config 已执行。用法: /config key=value" + f" args={argument}"
        return "[real] /config 已执行。用法: /config key=value"


COMMAND = ConfigCommand(
    name='config',
    summary='查看或设置配置项（如 provider/model）。',
    source_hint='src/commands/runtime/config/__init__.py',
)
