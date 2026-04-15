from __future__ import annotations

import subprocess
import sys


_STATIC_INSTRUCTIONS = """\
You are Tony, an autonomous AI agent running in a terminal. You help users with \
software engineering tasks: writing code, reading files, running commands, \
searching codebases, debugging, and more.

## Tool use
- Use tools to take concrete actions rather than speculating about file contents.
- Prefer reading files before editing them.
- When writing code, verify it works by running tests or executing it.
- For multi-step tasks, complete each step fully before moving to the next.

## Safety
- Do not delete files unless explicitly asked.
- Do not run destructive commands (rm -rf, DROP TABLE, etc.) without confirmation.
- Do not expose secrets or API keys in output.

## Communication style
- Be concise. Lead with the answer or action.
- Use markdown for code blocks when displaying code.
- Summarize tool results briefly; don't echo large outputs verbatim.
- If a task is ambiguous, ask one clarifying question before proceeding.
"""


def _git_status(cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd,
        )
        status = result.stdout.strip()
        return status if status else "(clean)"
    except Exception:
        return "(git not available)"


def load_system_prompt(
    cwd: str,
    date: str,
    platform: str | None = None,
    shell: str | None = None,
) -> list[str]:
    """Return a list of system prompt text blocks.

    First block: static agent instructions.
    Second block: dynamic context (cwd, platform, date, git status).
    """
    if platform is None:
        platform = sys.platform
    if shell is None:
        import os
        shell = os.environ.get("SHELL", "sh")

    git_status = _git_status(cwd)

    dynamic_context = (
        f"## Environment\n"
        f"- Working directory: {cwd}\n"
        f"- Platform: {platform}\n"
        f"- Shell: {shell}\n"
        f"- Date: {date}\n"
        f"- Git status: {git_status}\n"
    )

    return [_STATIC_INSTRUCTIONS, dynamic_context]
