from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..models import PortingBacklog, PortingModule
from .runtime import discover_runtime_commands

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / 'reference_data' / 'commands_snapshot.json'


@dataclass(frozen=True)
class CommandExecution:
    name: str
    source_hint: str
    prompt: str
    handled: bool
    message: str
    exit_repl: bool = False
    clear_screen: bool = False
    used_fallback: bool = False


@lru_cache(maxsize=1)
def load_command_snapshot() -> tuple[PortingModule, ...]:
    raw_entries = json.loads(SNAPSHOT_PATH.read_text())
    return tuple(
        PortingModule(
            name=entry['name'],
            responsibility=entry['responsibility'],
            source_hint=entry['source_hint'],
            status='mirrored',
        )
        for entry in raw_entries
    )


@lru_cache(maxsize=1)
def load_runtime_commands() -> tuple[PortingModule, ...]:
    return tuple(
        PortingModule(
            name=command.name,
            responsibility=command.summary,
            source_hint=command.source_hint,
            status='ported',
        )
        for command in discover_runtime_commands()
    )


@lru_cache(maxsize=1)
def runtime_command_map() -> dict[str, object]:
    return {command.name.lower(): command for command in discover_runtime_commands()}


@lru_cache(maxsize=1)
def merged_commands() -> tuple[PortingModule, ...]:
    modules = list(load_command_snapshot())
    modules.extend(load_runtime_commands())
    return tuple(modules)


PORTED_COMMANDS = merged_commands()


@lru_cache(maxsize=1)
def built_in_command_names() -> frozenset[str]:
    return frozenset(module.name for module in PORTED_COMMANDS)


def build_command_backlog() -> PortingBacklog:
    return PortingBacklog(title='Command surface', modules=list(PORTED_COMMANDS))


def command_names() -> list[str]:
    return [module.name for module in PORTED_COMMANDS]


def get_command(name: str) -> PortingModule | None:
    needle = name.lower()
    for module in PORTED_COMMANDS:
        if module.name.lower() == needle:
            return module
    return None


def get_commands(cwd: str | None = None, include_plugin_commands: bool = True, include_skill_commands: bool = True) -> tuple[PortingModule, ...]:
    commands = list(PORTED_COMMANDS)
    if not include_plugin_commands:
        commands = [module for module in commands if 'plugin' not in module.source_hint.lower()]
    if not include_skill_commands:
        commands = [module for module in commands if 'skills' not in module.source_hint.lower()]
    return tuple(commands)


def find_commands(query: str, limit: int = 20) -> list[PortingModule]:
    needle = query.lower()
    matches = [module for module in PORTED_COMMANDS if needle in module.name.lower() or needle in module.source_hint.lower()]
    return matches[:limit]


def execute_command(name: str, prompt: str = '') -> CommandExecution:
    runtime_command = runtime_command_map().get(name.lower())
    if runtime_command is not None:
        message = runtime_command.execute(prompt)
        normalized = runtime_command.name.lower()
        return CommandExecution(
            name=runtime_command.name,
            source_hint=runtime_command.source_hint,
            prompt=prompt,
            handled=True,
            message=message,
            exit_repl=normalized == 'exit',
            clear_screen=normalized == 'clear',
            used_fallback=False,
        )

    module = get_command(name)
    if module is None:
        return CommandExecution(name=name, source_hint='', prompt=prompt, handled=False, message=f'Unknown mirrored command: {name}')

    action = f"[shim fallback] Mirrored command '{module.name}' from {module.source_hint} would handle prompt {prompt!r}."
    return CommandExecution(
        name=module.name,
        source_hint=module.source_hint,
        prompt=prompt,
        handled=True,
        message=action,
        used_fallback=True,
    )


def render_command_index(limit: int = 20, query: str | None = None) -> str:
    modules = find_commands(query, limit) if query else list(PORTED_COMMANDS[:limit])
    lines = [f'Command entries: {len(PORTED_COMMANDS)}', '']
    if query:
        lines.append(f'Filtered by: {query}')
        lines.append('')
    lines.extend(f'- {module.name} — {module.source_hint}' for module in modules)
    return '\n'.join(lines)
