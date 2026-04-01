from __future__ import annotations

from ..base import RuntimeCommand


class HelpCommand(RuntimeCommand):
    def execute(self, prompt: str) -> str:
        argument = prompt.strip()
        if argument:
            return "[real] 可用命令：add-dir, branch, clear, commit, compact, config, context, cost, diff, doctor, exit, files, help, hooks, init, memory, model, permissions, plan, resume, review, session, usage" + f" args={argument}"
        return "[real] 可用命令：add-dir, branch, clear, commit, compact, config, context, cost, diff, doctor, exit, files, help, hooks, init, memory, model, permissions, plan, resume, review, session, usage"


COMMAND = HelpCommand(
    name='help',
    summary='列出可用命令与用法摘要。',
    source_hint='src/commands/runtime/help/__init__.py',
)
