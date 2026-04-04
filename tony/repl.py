from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .runtime import ConversationRuntime


def _supports_ansi() -> bool:
    return (
        sys.stdout.isatty()
        and os.environ.get("NO_COLOR") is None
        and os.environ.get("TERM") != "dumb"
    )


_BANNER_COLOR = (
    "\033[38;5;39m  ████████╗ ██████╗ ███╗   ██╗██╗   ██╗\033[0m\n"
    "\033[38;5;45m     ██╔══╝██╔═══██╗████╗  ██║╚██╗ ██╔╝\033[0m\n"
    "\033[38;5;51m     ██║   ██║   ██║██╔██╗ ██║ ╚████╔╝ \033[0m\n"
    "\033[38;5;87m     ██║   ██║   ██║██║╚██╗██║  ╚██╔╝  \033[0m\n"
    "\033[38;5;123m     ██║   ╚██████╔╝██║ ╚████║   ██║   \033[0m\n"
    "\033[38;5;159m     ╚═╝    ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   \033[0m\n"
    "\033[38;5;245m  AI Agent CLI  |  /help for commands  |  Ctrl-D to exit\033[0m\n"
)
_BANNER_PLAIN = "Tony | AI Agent CLI  (type /help for commands, Ctrl-D to exit)\n"
_BANNER = _BANNER_COLOR if _supports_ansi() else _BANNER_PLAIN


# ---------------------------------------------------------------------------
# Slash command implementations
# ---------------------------------------------------------------------------

def _cmd_help(runtime: "ConversationRuntime", _args: str) -> None:
    lines = ["Available slash commands:", ""]
    for name, (fn, desc) in _SLASH_COMMANDS.items():
        lines.append(f"  {name:<12} {desc}")
    print("\n".join(lines))


def _cmd_exit(runtime: "ConversationRuntime", _args: str) -> None:
    raise SystemExit(0)


def _cmd_status(runtime: "ConversationRuntime", _args: str) -> None:
    usage = runtime.usage_tracker.total
    msg_count = len(runtime.session.messages)
    print(
        f"Messages : {msg_count}\n"
        f"Tokens in: {usage.input_tokens}\n"
        f"Tokens out: {usage.output_tokens}"
    )


def _cmd_compact(runtime: "ConversationRuntime", _args: str) -> None:
    from .compressor import compact_session
    before = len(runtime.session.messages)
    runtime.session = compact_session(runtime.session, threshold_tokens=0)  # force compact
    after = len(runtime.session.messages)
    print(f"Compacted: {before} → {after} messages")


def _cmd_clear(runtime: "ConversationRuntime", _args: str) -> None:
    runtime.session.messages.clear()
    print("Session cleared.")


# name → (handler, description)
_SLASH_COMMANDS: dict[str, tuple[Callable, str]] = {
    "/help":    (_cmd_help,    "Show this help message"),
    "/exit":    (_cmd_exit,    "Exit tony"),
    "/status":  (_cmd_status,  "Show message count and token usage"),
    "/compact": (_cmd_compact, "Compact the session to save context"),
    "/clear":   (_cmd_clear,   "Clear the session history"),
}


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

def run_repl(runtime: "ConversationRuntime") -> None:
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

        if user_input.startswith("/"):
            # Find the command (first token) and pass remainder as args
            parts = user_input.split(None, 1)
            cmd_name = parts[0]
            cmd_args = parts[1] if len(parts) > 1 else ""
            entry = _SLASH_COMMANDS.get(cmd_name)
            if entry is None:
                print(f"Unknown command: {cmd_name}  (try /help)")
                continue
            handler, _ = entry
            try:
                handler(runtime, cmd_args)
            except SystemExit:
                raise
            except Exception as exc:
                print(f"Error: {exc}")
            continue

        # Normal user message → run turn
        try:
            for chunk in runtime.run_turn(user_input):
                print(chunk, end="", flush=True)
            print()  # trailing newline after stream
        except KeyboardInterrupt:
            print("\n[interrupted]")
        except Exception as exc:
            print(f"\nError: {exc}")
