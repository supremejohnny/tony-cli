from __future__ import annotations

import importlib
import pkgutil

from .base import RuntimeCommand


def discover_runtime_commands() -> tuple[RuntimeCommand, ...]:
    commands: list[RuntimeCommand] = []
    for module_info in pkgutil.iter_modules(__path__):
        if not module_info.ispkg:
            continue
        module = importlib.import_module(f'{__name__}.{module_info.name}')
        command = getattr(module, 'COMMAND', None)
        if isinstance(command, RuntimeCommand):
            commands.append(command)
    commands.sort(key=lambda item: item.name.lower())
    return tuple(commands)
