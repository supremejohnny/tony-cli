from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum


class PermissionMode(Enum):
    ALLOW = "allow"
    DENY = "deny"


# Tools that write to the filesystem or execute arbitrary code
_WRITE_TOOLS = {"bash", "write_file", "edit_file"}
_READ_ONLY_TOOLS = {"read_file", "glob_search", "grep_search"}


@dataclass
class PermissionPolicy:
    default_mode: PermissionMode = PermissionMode.ALLOW
    overrides: dict[str, PermissionMode] = field(default_factory=dict)

    # ------------------------------------------------------------------
    @classmethod
    def from_env(cls) -> "PermissionPolicy":
        mode_str = os.environ.get("TONY_PERMISSION_MODE", "workspace-write").lower()
        if mode_str == "read-only":
            # Deny all write/execute tools by default, allow read tools
            overrides = {tool: PermissionMode.DENY for tool in _WRITE_TOOLS}
            return cls(default_mode=PermissionMode.ALLOW, overrides=overrides)
        # workspace-write (default): allow everything
        return cls(default_mode=PermissionMode.ALLOW)

    # ------------------------------------------------------------------
    def authorize(self, tool_name: str, input: dict) -> PermissionMode:  # noqa: A002
        if tool_name in self.overrides:
            return self.overrides[tool_name]
        return self.default_mode
