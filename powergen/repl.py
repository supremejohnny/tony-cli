from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .mock_client import LLMClient
    from .state import ProjectState
    from .workspace import WorkspaceContext


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def _supports_ansi() -> bool:
    return (
        sys.stdout.isatty()
        and os.environ.get("NO_COLOR") is None
        and os.environ.get("TERM") != "dumb"
    )


_BANNER_COLOR = (
    "\033[38;5;208m  ██████╗  ██████╗ ██╗    ██╗███████╗██████╗  ██████╗ ███████╗███╗   ██╗\033[0m\n"
    "\033[38;5;214m  ██╔══██╗██╔═══██╗██║    ██║██╔════╝██╔══██╗██╔════╝ ██╔════╝████╗  ██║\033[0m\n"
    "\033[38;5;220m  ██████╔╝██║   ██║██║ █╗ ██║█████╗  ██████╔╝██║  ███╗█████╗  ██╔██╗ ██║\033[0m\n"
    "\033[38;5;226m  ██╔═══╝ ██║   ██║██║███╗██║██╔══╝  ██╔══██╗██║   ██║██╔══╝  ██║╚██╗██║\033[0m\n"
    "\033[38;5;46m  ██║     ╚██████╔╝╚███╔███╔╝███████╗██║  ██║╚██████╔╝███████╗██║ ╚████║\033[0m\n"
    "\033[38;5;51m  ╚═╝      ╚═════╝  ╚══╝╚══╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝\033[0m\n"
    "\033[38;5;245m  Presentation AI  |  /help for commands  |  Ctrl-D to exit\033[0m\n"
)

_BANNER_PLAIN = "PowerGen | Presentation AI  (type /help for commands, Ctrl-D to exit)\n"

_BANNER = _BANNER_COLOR if _supports_ansi() else _BANNER_PLAIN


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------

def _cmd_help(state: "ProjectState", client: "LLMClient", ws: "WorkspaceContext", args: str) -> None:
    lines = ["", "Available slash commands:", ""]
    for name, (_, desc) in _SLASH_COMMANDS.items():
        lines.append(f"  {name:<12} {desc}")
    lines.append("")
    print("\n".join(lines))


def _cmd_exit(state: "ProjectState", client: "LLMClient", ws: "WorkspaceContext", args: str) -> None:
    raise SystemExit(0)


def _cmd_status(state: "ProjectState", client: "LLMClient", ws: "WorkspaceContext", args: str) -> None:
    print(f"\n  Stage: {state.stage.value}")
    if state.plan:
        print(f"  Slides planned: {len(state.plan.slide_summaries)}")
    if state.spec:
        print(f"  Slides in spec: {len(state.spec.slides)}")
    if state.output_path:
        print(f"  Output: {state.output_path}")
    print()


def _cmd_create(state: "ProjectState", client: "LLMClient", ws: "WorkspaceContext", args: str) -> None:
    if not args.strip():
        print("Usage: /create <topic description>")
        return
    from .planner import generate_plan
    print("  Generating plan…")
    plan = generate_plan(args.strip(), ws, client, state)
    print(f"\n  Plan ready — {len(plan.slide_summaries)} slides")
    print(f"  Overview: {plan.overview}")
    if plan.open_questions:
        print("  Open questions:")
        for q in plan.open_questions:
            print(f"    · {q}")
    print()


def _cmd_revise(state: "ProjectState", client: "LLMClient", ws: "WorkspaceContext", args: str) -> None:
    if not args.strip():
        print("Usage: /revise <feedback>")
        return
    from .planner import revise_plan
    print("  Revising plan…")
    plan = revise_plan(args.strip(), ws, client, state)
    print(f"\n  Revised — now {len(plan.slide_summaries)} slides")
    print()


def _cmd_approve(state: "ProjectState", client: "LLMClient", ws: "WorkspaceContext", args: str) -> None:
    from .spec_builder import build_spec
    from .state import StateError
    if state.plan is None:
        print("  No plan yet. Run /create first.")
        return
    print("  [1/2] Locking plan…")
    print("  [2/2] Building slide spec…")
    try:
        spec = build_spec(state.plan, ws, client)
        state.advance_to_approved(spec)
        print(f"\n  Approved — {len(spec.slides)} slides ready to render")
        print(f"  Title: {spec.title}")
        print()
    except StateError as exc:
        print(f"  Error: {exc}")


def _cmd_render(state: "ProjectState", client: "LLMClient", ws: "WorkspaceContext", args: str) -> None:
    from .renderer import render_presentation
    from .state import StateError
    if state.spec is None:
        print("  No approved spec. Run /approve first.")
        return
    template_path = None
    if state.spec.theme_reference:
        from pathlib import Path
        candidate = Path.cwd() / state.spec.theme_reference
        if candidate.exists():
            template_path = candidate
    output_arg = args.strip() or None
    output_path = None if output_arg is None else __import__("pathlib").Path(output_arg)
    try:
        out = render_presentation(state.spec, output_path=output_path, template_path=template_path)
        state.advance_to_rendered(str(out))
        print(f"\n  Rendered: {out}\n")
    except StateError as exc:
        print(f"  Error: {exc}")


def _cmd_reset(state: "ProjectState", client: "LLMClient", ws: "WorkspaceContext", args: str) -> None:
    state.reset()
    print("  Project reset to INIT.\n")


# name → (handler, description)
_SLASH_COMMANDS: dict[str, tuple[Callable, str]] = {
    "/help":    (_cmd_help,    "Show this help message"),
    "/exit":    (_cmd_exit,    "Exit powergen"),
    "/status":  (_cmd_status,  "Show current project stage"),
    "/create":  (_cmd_create,  "Generate a plan  (args: <topic>)"),
    "/revise":  (_cmd_revise,  "Revise plan with feedback  (args: <feedback>)"),
    "/approve": (_cmd_approve, "Approve plan and build slide spec"),
    "/render":  (_cmd_render,  "Render spec to .pptx  (args: optional output path)"),
    "/reset":   (_cmd_reset,   "Reset project state to INIT"),
}


# ---------------------------------------------------------------------------
# REPL loop
# ---------------------------------------------------------------------------

def run_repl(
    state: "ProjectState",
    client: "LLMClient",
    workspace: "WorkspaceContext",
) -> None:
    print(_BANNER, end="")

    while True:
        try:
            user_input = input("> ").strip()
        except KeyboardInterrupt:
            print()
            continue
        except EOFError:
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        parts = user_input.split(None, 1)
        cmd_name = parts[0]
        cmd_args = parts[1] if len(parts) > 1 else ""

        entry = _SLASH_COMMANDS.get(cmd_name)
        if entry is None:
            # If it starts with / it's an unknown command; otherwise hint the user
            if cmd_name.startswith("/"):
                print(f"  Unknown command: {cmd_name}  (try /help)")
            else:
                print("  Type /create <topic> to start, or /help for commands.")
            continue

        handler, _ = entry
        try:
            handler(state, client, workspace, cmd_args)
        except SystemExit:
            raise
        except Exception as exc:
            print(f"  Error: {exc}")
