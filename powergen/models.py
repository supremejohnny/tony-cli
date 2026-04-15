from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SlideSpec:
    index: int
    title: str
    bullets: list[str]
    layout: str          # layout name from template, or "blank"
    notes: str = ""
    assets: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "title": self.title,
            "bullets": self.bullets,
            "layout": self.layout,
            "notes": self.notes,
            "assets": self.assets,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SlideSpec":
        return cls(
            index=d["index"],
            title=d["title"],
            bullets=d.get("bullets", []),
            layout=d.get("layout", "blank"),
            notes=d.get("notes", ""),
            assets=d.get("assets", []),
        )


@dataclass
class PresentationSpec:
    title: str
    audience: str
    tone: str
    theme_reference: str          # template .pptx filename, or ""
    slides: list[SlideSpec] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "audience": self.audience,
            "tone": self.tone,
            "theme_reference": self.theme_reference,
            "slides": [s.to_dict() for s in self.slides],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PresentationSpec":
        return cls(
            title=d["title"],
            audience=d.get("audience", ""),
            tone=d.get("tone", "professional"),
            theme_reference=d.get("theme_reference", ""),
            slides=[SlideSpec.from_dict(s) for s in d.get("slides", [])],
        )


@dataclass
class PlanDocument:
    overview: str
    slide_summaries: list[str]    # one per intended slide
    references: list[str]         # workspace files cited
    open_questions: list[str]

    def to_dict(self) -> dict:
        return {
            "overview": self.overview,
            "slide_summaries": self.slide_summaries,
            "references": self.references,
            "open_questions": self.open_questions,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PlanDocument":
        return cls(
            overview=d.get("overview", ""),
            slide_summaries=d.get("slide_summaries", []),
            references=d.get("references", []),
            open_questions=d.get("open_questions", []),
        )
