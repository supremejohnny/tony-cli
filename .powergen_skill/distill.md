# powergen distill

Pre-processes all workspace files into structured `.distill.json` knowledge artifacts stored in `.powergen_distill/`. Provides a persistent, queryable context layer for downstream generation commands (`create`, `template`).

## Commands

```bash
powergen distill           # distill all supported files, skip unchanged
powergen distill --force   # re-distill everything regardless of hash
powergen distill --model <model>  # override model (default: claude-haiku-4-5-20251001)
```

`template` runs distill automatically as a pre-step. If nothing has changed it completes in under a second.

## Supported file types

| Extension | Extraction method | Chunking |
|---|---|---|
| `.pptx` | python-pptx, per-slide title + body | Slide-aware: 1–4 slides per chunk, merges by title continuity / text sparsity |
| `.pdf`, `.docx` | markitdown | Semantic: by heading or topic shift |
| `.md`, `.txt` | plain read | Semantic: by heading or topic shift |

## What happens, step by step

1. Scan workspace for supported files
2. For each file: SHA256 hash → compare against stored hash → skip if unchanged (zero API calls)
3. Extract text per file type (see table above)
4. Send to LLM (Haiku) with chunking rules and output schema
5. LLM returns chunk boundaries + semantic fields
6. **PPTX only**: inject `combined_text` locally by slicing extracted slides using `slide_range` — LLM never outputs it, saves ~30-40% output tokens and guarantees verbatim content
7. Stamp `file_hash` + `distilled_at`, write `{stem}.distill.json`
8. Update `_index.json`

## Output structure

```
.powergen_distill/
  lecture.distill.json     ← one per source file
  notes.distill.json
  _index.json              ← collection-level index
```

Nested files get collision-safe names: `rust/README.md` → `rust_README.distill.json`.

## distill JSON schema

```json
{
  "version": "1.0",
  "source": {
    "file_name": "lecture.pptx",
    "file_hash": "sha256:abc123...",
    "distilled_at": "2026-04-07T10:00:00Z"
  },
  "global_summary": "2-4 sentence overview of the entire file.",
  "main_topics": ["topic A", "topic B"],
  "chunks": [
    {
      "chunk_id": "chunk_01",
      "slide_range": [1, 3],
      "titles": ["Intro", "Paging Basics"],
      "combined_text": "=== Slide 1: Intro ===\n...\n\n=== Slide 2 ===\n...",
      "summary_short": "1-2 sentence description of this chunk.",
      "key_points": [
        "Declarative takeaway 1.",
        "Declarative takeaway 2."
      ],
      "definitions": [
        {"term": "paging", "definition": "Only present if source has an explicit 'X is ...' sentence."}
      ],
      "entities": ["paging", "page table", "TLB"],
      "question_signatures": [
        "What is paging?",
        "How does address translation work?"
      ],
      "keywords": ["paging", "page table", "frame"],
      "anchors": {
        "start_slide": 1,
        "end_slide": 3,
        "prev_title": null,
        "next_title": "TLB"
      }
    }
  ]
}
```

**Field notes**
- `combined_text` — verbatim source text; local-injected for `.pptx`, LLM-output for text files
- `definitions` — only terms with explicit definition sentences in the source; `[]` otherwise
- `slide_range` / `anchors` — PPTX only; text files use `chunk_id` like `section_01`

## _index.json schema

```json
[
  {
    "source_file": "lecture.pptx",
    "distill_file": "lecture.distill.json",
    "file_hash": "sha256:abc123...",
    "distilled_at": "2026-04-07T10:00:00Z",
    "global_summary": "...",
    "main_topics": ["topic A", "topic B"]
  }
]
```

Used by `create` and `template` to pre-filter relevant files without loading all chunk data.

## Key files

- `powergen/distiller.py` — extraction, hashing, LLM call, local injection, index update
- `powergen/prompts_distill.py` — PPTX and generic prompt pairs with schema and chunking rules
- `powergen/cli.py` — `distill` subparser; `template` auto-runs distill as pre-step
