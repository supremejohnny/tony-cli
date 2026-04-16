# powergen/

AI presentation generator. Three layers of progressive capability.

## Directory structure

```
powergen/
├── cli.py              # entry point (powergen command)
├── models.py           # PlanDocument, PresentationSpec, SlideSpec
├── state.py            # project state machine (INIT → PLANNED → APPROVED → RENDERED)
├── workspace.py        # scan working directory for templates / content files
├── planner.py          # Layer 1: LLM plan generation
├── spec_builder.py     # Layer 1: LLM spec building
├── renderer.py         # Layer 1: deterministic pptx rendering
├── prompts.py          # Layer 1: plan + spec prompts
├── mock_client.py      # zero-token mock LLM client (--mock flag)
├── repl.py             # interactive REPL mode
├── template_reader.py  # shared: read slide layouts from a .pptx
│
├── layer2/             # Layer 2: schema-based template composition
│   ├── SKILL.md        # how to author a template.schema.json
│   ├── schemas/        # one .schema.json per template
│   │   └── test_template.schema.json
│   ├── composer/       # Composer code (deterministic Python)
│   │   ├── schema_gen.py    # local pptx → schema extraction (no LLM)
│   │   ├── schema_loader.py # load + strip _comment fields from schema JSON
│   │   ├── slot_resolver.py # resolve shape_name / nth / near locators
│   │   ├── slide_cloner.py  # clone reusable slide + fill slots (lxml + OPC)
│   │   ├── composer.py      # orchestrate clone + renderer calls
│   │   ├── planner.py       # Composer LLM call + mock_plan()
│   │   └── renderers/       # one module per content_type
│   │       ├── card.py, bullet.py, flow.py
│   └── scripts/
│       ├── validate.py      # validate schema locators against source .pptx
│       └── inspect_pptx.py  # dump shape inventory from .pptx
│
└── scripts/office/     # OOXML tools: pack, unpack, validate XML
```

## Layer 1 — Scaffold

Generate a structured skeleton from a topic description.

```bash
# with real API
powergen create "your topic"
powergen approve
powergen render

# zero tokens (mock)
powergen --mock create "your topic"
powergen --mock approve
powergen --mock render

# interactive REPL
powergen --mock
```

## Layer 2 — Schema-based template composition

Point at any `.pptx` template — schema is auto-generated locally and cached.

```bash
# primary usage: auto-schema from pptx (schema cached as <pptx>.schema.json)
powergen template --pptx my_template.pptx --topic "your topic" --output out.pptx

# with cheaper model
powergen --model claude-haiku-4-5-20251001 template --pptx my_template.pptx --topic "..."

# zero tokens (mock, exercises full code path)
powergen --mock template --pptx my_template.pptx --topic "..." --output out.pptx

# advanced: hand-authored schema (full slot control)
powergen template --schema powergen/layer2/schemas/test_template.schema.json --topic "..."

# tooling
python -m powergen.layer2.scripts.inspect_pptx my_template.pptx   # shape inventory
python -m powergen.layer2.scripts.validate my_template.schema.json # validate schema
```

**Known issues (in progress)**:
- Some PLACEHOLDER-type shapes not resolved after slide clone → original template text shows through
- Theme fonts (`+mj-lt`, `+mn-lt`) may fall back to system default in cloned slides → visual formatting degradation

## Layer 3 — Full Visual

Not started. See `POWERGEN_ROADMAP.md`.
