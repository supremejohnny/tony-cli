# powergen distill

Pre-processes all workspace files into structured `.distill.json` knowledge artifacts stored in `.powergen_distill/`. Provides a persistent, queryable context layer for downstream generation commands (`create`, `template`).

## Commands

```bash
powergen distill                   # distill all supported files, skip unchanged
powergen distill --force           # re-distill everything regardless of hash
powergen distill --model <model>   # override model (default: claude-haiku-4-5-20251001)
powergen --no-vision distill       # skip image vision processing (reduces API cost)
```

`template` runs distill automatically as a pre-step. If nothing has changed it completes in under a second.

`--no-vision` is a top-level flag (before the subcommand) and applies to both `distill` and `template`.

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
4. **PPTX + vision enabled**: extract embedded images from all shapes (including `PLACEHOLDER` and nested group shapes); filter decorative images by area (< 5% of slide) and margin position (centre in outer 10%); skip blobs > 3.5 MB
5. Send text to LLM (Haiku) with chunking rules and output schema
6. LLM returns chunk boundaries + semantic fields
7. **PPTX only**: inject `combined_text` locally by slicing extracted slides using `slide_range` — LLM never outputs it, saves ~30-40% output tokens and guarantees verbatim content
8. **PPTX + vision enabled**: batch images by slide → one `generate_vision()` call per slide → append `[Visual: ...]` descriptions to `combined_text`; set `has_images: true` on affected chunks
9. Stamp `file_hash` + `distilled_at`, write `{stem}.distill.json`
10. Update `_index.json`

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
      "combined_text": "=== Slide 1: Intro ===\n...\n\n=== Slide 2 ===\n(no text)\n[Visual: A binary tree diagram. Root node is '+', left subtree '1', right subtree '*' with children '2' and '3'.]",
      "has_images": true,
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
- `combined_text` — verbatim source text; local-injected for `.pptx`, LLM-output for text files; vision descriptions appended as `[Visual: ...]` lines when images are present
- `has_images` — `true` if any slide in this chunk had a non-decorative image processed by vision; PPTX only; absent for text-file chunks
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

- `powergen/distiller.py` — extraction, hashing, LLM call, local injection, vision image extraction, index update
- `powergen/prompts_distill.py` — PPTX and generic prompt pairs with schema and chunking rules; vision system/user prompts
- `powergen/mock_client.py` — `LLMClient` protocol (incl. `generate_vision()`), real and mock implementations
- `powergen/cli.py` — `distill` subparser; `--no-vision` top-level flag; `template` auto-runs distill as pre-step
