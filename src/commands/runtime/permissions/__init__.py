from __future__ import annotations

from ..base import RuntimeCommand


class PermissionsCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /permissions 已执行。查看工具权限状态。" + f" args={argument}"
        return "[real] /permissions 已执行。查看工具权限状态。"


COMMAND = PermissionsCommand(
    name='permissions',
    summary='查看工具权限状态。',
    source_hint='src/commands/runtime/permissions/__init__.py',
)
