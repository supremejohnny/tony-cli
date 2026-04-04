from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .models import PlanDocument, PresentationSpec

_STATE_DIR = ".powergen"
_STATE_FILE = "project.json"

_STAGE_ORDER = {"INIT": 0, "PLANNED": 1, "APPROVED": 2, "RENDERED": 3}


class Stage(Enum):
    INIT = "INIT"
    PLANNED = "PLANNED"
    APPROVED = "APPROVED"
    RENDERED = "RENDERED"


class StateError(RuntimeError):
    """Raised when a stage precondition is violated."""


@dataclass
class ProjectState:
    stage: Stage = Stage.INIT
    plan: PlanDocument | None = None
    spec: PresentationSpec | None = None
    output_path: str | None = None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, project_dir: Path | None = None) -> None:
        root = project_dir or Path.cwd()
        state_dir = root / _STATE_DIR
        state_dir.mkdir(exist_ok=True)
        state_path = state_dir / _STATE_FILE
        data = {
            "stage": self.stage.value,
            "plan": self.plan.to_dict() if self.plan else None,
            "spec": self.spec.to_dict() if self.spec else None,
            "output_path": self.output_path,
        }
        state_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, project_dir: Path | None = None) -> "ProjectState":
        root = project_dir or Path.cwd()
        state_path = root / _STATE_DIR / _STATE_FILE
        if not state_path.exists():
            return cls()
        data = json.loads(state_path.read_text(encoding="utf-8"))
        return cls(
            stage=Stage(data.get("stage", "INIT")),
            plan=PlanDocument.from_dict(data["plan"]) if data.get("plan") else None,
            spec=PresentationSpec.from_dict(data["spec"]) if data.get("spec") else None,
            output_path=data.get("output_path"),
        )

    # ------------------------------------------------------------------
    # Stage transitions
    # ------------------------------------------------------------------

    def _require_min_stage(self, minimum: Stage, action: str) -> None:
        if _STAGE_ORDER[self.stage.value] < _STAGE_ORDER[minimum.value]:
            raise StateError(
                f"Cannot {action}: current stage is {self.stage.value}, "
                f"need at least {minimum.value}."
            )

    def advance_to_planned(self, plan: PlanDocument) -> None:
        if not plan.slide_summaries:
            raise StateError("Plan must include at least one slide summary.")
        self.plan = plan
        self.stage = Stage.PLANNED
        self.save()

    def advance_to_approved(self, spec: PresentationSpec) -> None:
        self._require_min_stage(Stage.PLANNED, "approve")
        if not spec.slides:
            raise StateError("Spec must include at least one slide before approving.")
        self.spec = spec
        self.stage = Stage.APPROVED
        self.save()

    def advance_to_rendered(self, output_path: str) -> None:
        self._require_min_stage(Stage.APPROVED, "render")
        self.output_path = output_path
        self.stage = Stage.RENDERED
        self.save()

    def reset(self) -> None:
        self.stage = Stage.INIT
        self.plan = None
        self.spec = None
        self.output_path = None
        self.save()
