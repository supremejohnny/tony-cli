from __future__ import annotations

import difflib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# ToolSpec
# ---------------------------------------------------------------------------

@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict

    def to_api_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


# ---------------------------------------------------------------------------
# bash
# ---------------------------------------------------------------------------

def _tool_bash(cmd: str, timeout: int = 120, background: bool = False) -> str:
    if background:
        proc = subprocess.Popen(
            ["sh", "-lc", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return f"Background process started (pid={proc.pid})"
    try:
        result = subprocess.run(
            ["sh", "-lc", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += result.stderr
        return output if output else "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s"
    except Exception as exc:
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

def _tool_read_file(path: str, offset: int = 0, limit: int | None = None) -> str:
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as exc:
        return f"Error reading file: {exc}"

    if offset:
        lines = lines[offset:]
    if limit is not None:
        lines = lines[:limit]

    start_line = offset + 1
    numbered = [f"{start_line + i}\t{line}" for i, line in enumerate(lines)]
    return "\n".join(numbered)


# ---------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------

def _tool_write_file(path: str, content: str) -> str:
    p = Path(path)
    old_content = ""
    if p.exists():
        try:
            old_content = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    except Exception as exc:
        return f"Error writing file: {exc}"

    diff_lines = list(difflib.unified_diff(
        old_content.splitlines(keepends=True),
        content.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    ))
    if diff_lines:
        return "".join(diff_lines)
    return f"File written: {path} (no changes)"


# ---------------------------------------------------------------------------
# edit_file
# ---------------------------------------------------------------------------

def _tool_edit_file(path: str, old_string: str, new_string: str) -> str:
    try:
        content = Path(path).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as exc:
        return f"Error reading file: {exc}"

    count = content.count(old_string)
    if count == 0:
        return f"Error: old_string not found in {path}"
    if count > 1:
        return f"Error: old_string found {count} times in {path} — must be unique"

    new_content = content.replace(old_string, new_string, 1)
    diff_lines = list(difflib.unified_diff(
        content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    ))
    try:
        Path(path).write_text(new_content, encoding="utf-8")
    except Exception as exc:
        return f"Error writing file: {exc}"

    return "".join(diff_lines) if diff_lines else f"Edit applied to {path}"


# ---------------------------------------------------------------------------
# glob_search
# ---------------------------------------------------------------------------

def _tool_glob_search(pattern: str, base_path: str = ".") -> str:
    try:
        base = Path(base_path)
        matches = sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception as exc:
        return f"Error: {exc}"

    if not matches:
        return "No matches found"
    return "\n".join(str(p) for p in matches)


# ---------------------------------------------------------------------------
# grep_search
# ---------------------------------------------------------------------------

def _tool_grep_search(
    pattern: str,
    path: str = ".",
    glob: str = "**/*",
    context: int = 0,
    case_insensitive: bool = False,
) -> str:
    flags = re.IGNORECASE if case_insensitive else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as exc:
        return f"Error: invalid regex: {exc}"

    results: list[str] = []
    base = Path(path)
    try:
        candidates = [p for p in base.glob(glob) if p.is_file()]
    except Exception as exc:
        return f"Error: {exc}"

    for file_path in sorted(candidates):
        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines):
            if regex.search(line):
                start = max(0, i - context)
                end = min(len(lines), i + context + 1)
                for j in range(start, end):
                    prefix = ">" if j == i else " "
                    results.append(f"{file_path}:{j + 1}{prefix} {lines[j]}")
                results.append("")

    return "\n".join(results).rstrip() if results else "No matches found"


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

_TOOL_HANDLERS: dict[str, Any] = {
    "bash": lambda inp: _tool_bash(
        inp["command"],
        timeout=int(inp.get("timeout", 120)),
        background=bool(inp.get("background", False)),
    ),
    "read_file": lambda inp: _tool_read_file(
        inp["path"],
        offset=int(inp.get("offset", 0)),
        limit=inp.get("limit"),
    ),
    "write_file": lambda inp: _tool_write_file(inp["path"], inp["content"]),
    "edit_file": lambda inp: _tool_edit_file(inp["path"], inp["old_string"], inp["new_string"]),
    "glob_search": lambda inp: _tool_glob_search(
        inp["pattern"],
        base_path=inp.get("base_path", "."),
    ),
    "grep_search": lambda inp: _tool_grep_search(
        inp["pattern"],
        path=inp.get("path", "."),
        glob=inp.get("glob", "**/*"),
        context=int(inp.get("context", 0)),
        case_insensitive=bool(inp.get("case_insensitive", False)),
    ),
}


def execute_tool(name: str, input_json: dict) -> str:
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        return f"Error: unknown tool '{name}'"
    try:
        return handler(input_json)
    except KeyError as exc:
        return f"Error: missing required parameter {exc}"
    except Exception as exc:
        return f"Error executing {name}: {exc}"


# ---------------------------------------------------------------------------
# Tool specs (JSON Schema)
# ---------------------------------------------------------------------------

def mvp_tool_specs() -> list[ToolSpec]:
    return [
        ToolSpec(
            name="bash",
            description=(
                "Execute a shell command. Returns stdout+stderr. "
                "Use background=true to launch a fire-and-forget process."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 120)", "default": 120},
                    "background": {"type": "boolean", "description": "Run in background (default false)", "default": False},
                },
                "required": ["command"],
            },
        ),
        ToolSpec(
            name="read_file",
            description="Read a file from the filesystem, optionally slicing by line offset/limit.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative path to the file"},
                    "offset": {"type": "integer", "description": "First line to read (0-indexed)", "default": 0},
                    "limit": {"type": "integer", "description": "Maximum number of lines to return"},
                },
                "required": ["path"],
            },
        ),
        ToolSpec(
            name="write_file",
            description="Write content to a file. Returns a unified diff of the changes.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "content": {"type": "string", "description": "Full content to write"},
                },
                "required": ["path", "content"],
            },
        ),
        ToolSpec(
            name="edit_file",
            description=(
                "Replace a unique old_string with new_string in a file. "
                "Fails if old_string is not found or appears more than once."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "old_string": {"type": "string", "description": "Exact text to find (must be unique)"},
                    "new_string": {"type": "string", "description": "Replacement text"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        ),
        ToolSpec(
            name="glob_search",
            description="Find files matching a glob pattern, sorted by modification time (newest first).",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern e.g. '**/*.py'"},
                    "base_path": {"type": "string", "description": "Directory to search from (default '.')", "default": "."},
                },
                "required": ["pattern"],
            },
        ),
        ToolSpec(
            name="grep_search",
            description="Search file contents with a regex pattern. Returns matching lines with optional context.",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {"type": "string", "description": "Directory to search in (default '.')", "default": "."},
                    "glob": {"type": "string", "description": "File glob filter (default '**/*')", "default": "**/*"},
                    "context": {"type": "integer", "description": "Lines of context around each match", "default": 0},
                    "case_insensitive": {"type": "boolean", "description": "Case-insensitive search", "default": False},
                },
                "required": ["pattern"],
            },
        ),
    ]
