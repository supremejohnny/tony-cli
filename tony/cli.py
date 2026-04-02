from __future__ import annotations

import argparse
import os
import sys
from datetime import date


def _build_runtime(model: str, resume: str | None = None):
    """Construct a ConversationRuntime, optionally resuming from a saved session."""
    from .api_client import AnthropicClient
    from .models import Session
    from .permissions import PermissionPolicy
    from .runtime import CliToolExecutor, ConversationRuntime
    from .system_prompt import load_system_prompt

    api_client = AnthropicClient(model=model)
    policy = PermissionPolicy.from_env()
    tool_executor = CliToolExecutor(policy)

    if resume:
        session = Session.load(resume)
    else:
        session = Session()

    cwd = os.getcwd()
    today = date.today().isoformat()
    system_blocks = load_system_prompt(cwd=cwd, date=today)

    return ConversationRuntime(
        session=session,
        api_client=api_client,
        tool_executor=tool_executor,
        permission_policy=policy,
        model=model,
        system_blocks=system_blocks,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tony",
        description="Tony — AI agent CLI",
    )
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Model ID to use")
    parser.add_argument("--resume", metavar="SESSION_FILE", help="Resume a saved session")

    subparsers = parser.add_subparsers(dest="cmd")

    # tony prompt "..."
    prompt_parser = subparsers.add_parser("prompt", help="Run a single prompt and exit")
    prompt_parser.add_argument("text", help="The prompt to send")

    # tony system-prompt
    subparsers.add_parser("system-prompt", help="Print the system prompt and exit")

    args = parser.parse_args(argv)

    if args.cmd == "system-prompt":
        from .system_prompt import load_system_prompt
        blocks = load_system_prompt(cwd=os.getcwd(), date=date.today().isoformat())
        print("\n\n".join(blocks))
        return 0

    if args.cmd == "prompt":
        runtime = _build_runtime(model=args.model, resume=getattr(args, "resume", None))
        try:
            for chunk in runtime.run_turn(args.text):
                print(chunk, end="", flush=True)
            print()
        except EnvironmentError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        return 0

    # Default: interactive REPL
    from .repl import run_repl
    try:
        runtime = _build_runtime(model=args.model, resume=getattr(args, "resume", None))
    except EnvironmentError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        run_repl(runtime)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
