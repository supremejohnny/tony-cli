from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_TEMPLATE_EXTS = {".pptx"}
_CONTENT_EXTS = {".md", ".txt", ".docx", ".pdf"}
_DATA_EXTS = {".json", ".csv"}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".gif"}


@dataclass
class WorkspaceFile:
    path: Path
    file_type: str    # "template" | "content" | "data" | "image"
    size_bytes: int


@dataclass
class TemplateInfo:
    path: Path
    layouts: list[str] = field(default_factory=list)


@dataclass
class WorkspaceContext:
    templates: list[TemplateInfo] = field(default_factory=list)
    content_files: list[WorkspaceFile] = field(default_factory=list)
    data_files: list[WorkspaceFile] = field(default_factory=list)
    image_files: list[WorkspaceFile] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        lines: list[str] = []
        if self.templates:
            lines.append(f"Templates ({len(self.templates)}):")
            for t in self.templates:
                layout_str = ", ".join(t.layouts[:5])
                if len(t.layouts) > 5:
                    layout_str += f" ... +{len(t.layouts) - 5} more"
                lines.append(f"  {t.path.name}  [layouts: {layout_str or 'none'}]")
        if self.content_files:
            lines.append(f"Content ({len(self.content_files)}): " +
                         ", ".join(f.path.name for f in self.content_files[:8]))
        if self.data_files:
            lines.append(f"Data ({len(self.data_files)}): " +
                         ", ".join(f.path.name for f in self.data_files[:8]))
        if self.image_files:
            lines.append(f"Images ({len(self.image_files)}): " +
                         ", ".join(f.path.name for f in self.image_files[:8]))
        if not lines:
            lines.append("(no relevant files found in workspace)")
        return lines


def _extract_layouts(pptx_path: Path) -> list[str]:
    try:
        from pptx import Presentation  # type: ignore[import]
        prs = Presentation(str(pptx_path))
        return [layout.name for layout in prs.slide_layouts]
    except Exception:
        return []


def scan_workspace(root: Path | None = None) -> WorkspaceContext:
    root = root or Path.cwd()
    ctx = WorkspaceContext()

    for p in sorted(root.rglob("*")):
        # Skip hidden dirs (e.g. .powergen, .git)
        if any(part.startswith(".") for part in p.parts[len(root.parts):]):
            continue
        if not p.is_file():
            continue

        ext = p.suffix.lower()
        size = p.stat().st_size

        if ext in _TEMPLATE_EXTS:
            # Exclude powergen output files from being treated as templates
            if p.stem.endswith(("-filled", "-generated")):
                continue
            layouts = _extract_layouts(p)
            ctx.templates.append(TemplateInfo(path=p, layouts=layouts))
        elif ext in _CONTENT_EXTS:
            ctx.content_files.append(WorkspaceFile(path=p, file_type="content", size_bytes=size))
        elif ext in _DATA_EXTS:
            ctx.data_files.append(WorkspaceFile(path=p, file_type="data", size_bytes=size))
        elif ext in _IMAGE_EXTS:
            ctx.image_files.append(WorkspaceFile(path=p, file_type="image", size_bytes=size))

    return ctx
