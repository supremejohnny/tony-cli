from __future__ import annotations

from ..base import RuntimeCommand


class FilesCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] /files 已执行。列出文件上下文状态。" + f" args={argument}"
        return "[real] /files 已执行。列出文件上下文状态。"


COMMAND = FilesCommand(
    name='files',
    summary='列出文件上下文状态。',
    source_hint='src/commands/runtime/files/__init__.py',
)
