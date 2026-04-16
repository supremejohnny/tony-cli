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
│   └── scripts/
│       └── validate.py # validate schema locators against source .pptx
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

Composer not yet implemented. Schema tooling available:

```bash
# validate a template schema against its source .pptx
python -m powergen.layer2.scripts.validate powergen/layer2/schemas/test_template.schema.json
```

See [layer2/SKILL.md](layer2/SKILL.md) for how to author a schema for a new template.

## Layer 3 — Full Visual

Not started. See `POWERGEN_ROADMAP.md`.
