from __future__ import annotations

# ---------------------------------------------------------------------------
# Distill prompts — PPT (slide-aware chunking)
# ---------------------------------------------------------------------------
#
# combined_text is intentionally absent from the PPTX schema.
# It is injected locally by distiller.py after the LLM call, using the
# slide_range returned by the model to slice the already-extracted SlideText
# list. This avoids spending output tokens on verbatim text the caller
# already has, and guarantees the field is truly verbatim (not LLM-paraphrased).

_PPTX_CHUNK_SCHEMA = """{
  "version": "1.0",
  "source": {
    "file_name": "<original filename>",
    "file_hash": "",
    "distilled_at": ""
  },
  "global_summary": "<2-4 sentence overview of the entire file>",
  "main_topics": ["<topic 1>", "<topic 2>"],
  "chunks": [
    {
      "chunk_id": "chunk_01",
      "slide_range": [1, 3],
      "titles": ["<slide 1 title>", "<slide 3 title>"],
      "summary_short": "<1-2 sentences: what this chunk is about>",
      "key_points": ["<key point 1>", "<key point 2>", "<key point 3>"],
      "definitions": [
        {"term": "<term>", "definition": "<definition>"}
      ],
      "entities": ["<concept, system, or technique name>"],
      "question_signatures": [
        "<question this chunk can answer, e.g. What is X?>",
        "<another question>"
      ],
      "keywords": ["<keyword 1>", "<keyword 2>"],
      "anchors": {
        "start_slide": 1,
        "end_slide": 3,
        "prev_title": null,
        "next_title": "<title of first slide in next chunk, or null>"
      }
    }
  ]
}"""


def distill_pptx_system_prompt() -> str:
    return f"""\
You are a knowledge distiller. Your job is to read a set of presentation slides \
and produce a structured knowledge artifact that is readable, searchable, \
answerable, and traceable.

Chunking rules (apply in order):
1. Start with one chunk per slide as the base unit.
2. Merge adjacent slides into a single chunk when ANY of these conditions hold:
   a. Their titles belong to the same section or topic (e.g. "Paging" and "Paging Example").
   b. A slide continues, illustrates, or summarises the previous slide.
   c. A slide has very sparse text (fewer than ~15 words) and is not a standalone concept.
3. Never merge more than 4 slides into one chunk.
4. A pure title/divider slide with no body text should be absorbed into the next chunk.

For each chunk:
- summary_short: 1-2 sentences describing what the chunk covers.
- key_points: 2-4 important takeaways, as short declarative sentences.
- definitions: ONLY include if the source text contains an explicit definition sentence \
for a domain-specific technical term (e.g. "X is ...", "X: definition"). \
Option labels, section headings, and general descriptions do NOT qualify. \
Use an empty list [] if no such definitions exist.
- entities: notable concepts, systems, algorithms, or proper nouns mentioned.
- question_signatures: 2-3 natural questions a reader would ask that this chunk answers.
- keywords: 3-5 retrieval keywords.
- anchors: slide numbers and neighbouring chunk titles for traceability.

Respond with ONLY a JSON object that matches this exact schema:
{_PPTX_CHUNK_SCHEMA}

Rules:
- file_hash and distilled_at will be filled in by the caller — set them to empty strings "".
- No markdown fences, no extra commentary — just the JSON object."""


def distill_pptx_user_prompt(file_name: str, slide_text: str) -> str:
    return f"""\
File: {file_name}

--- Slides ---
{slide_text}

Produce the distill JSON for this file."""


# ---------------------------------------------------------------------------
# Distill prompts — generic text (PDF, DOCX, MD, TXT)
# ---------------------------------------------------------------------------
#
# combined_text is kept in the generic schema because the LLM determines
# chunk boundaries for free-form text (no reliable slide_range to slice from).

_GENERIC_CHUNK_SCHEMA = """{
  "version": "1.0",
  "source": {
    "file_name": "<original filename>",
    "file_hash": "",
    "distilled_at": ""
  },
  "global_summary": "<2-4 sentence overview of the entire file>",
  "main_topics": ["<topic 1>", "<topic 2>"],
  "chunks": [
    {
      "chunk_id": "section_01",
      "titles": ["<section heading, or 'Main Content' if no headings>"],
      "combined_text": "<verbatim text of this section>",
      "summary_short": "<1-2 sentences: what this section covers>",
      "key_points": ["<key point 1>", "<key point 2>"],
      "definitions": [
        {"term": "<term>", "definition": "<definition>"}
      ],
      "entities": ["<concept or proper noun>"],
      "question_signatures": ["<question this section answers>"],
      "keywords": ["<keyword 1>", "<keyword 2>"]
    }
  ]
}"""


def distill_generic_system_prompt() -> str:
    return f"""\
You are a knowledge distiller. Your job is to read a document and produce a \
structured knowledge artifact that is readable, searchable, answerable, and traceable.

Chunking rules:
1. Split the document into logical sections based on headings or topic shifts.
2. If the document has no headings, treat it as a single chunk.
3. Keep chunks between roughly 200 and 800 words of source text.
4. Never split a paragraph in the middle.

For each chunk:
- combined_text: copy the section text verbatim (do not summarise here).
- summary_short: 1-2 sentences describing what the section covers.
- key_points: 2-4 important takeaways, as short declarative sentences.
- definitions: ONLY include if the source text contains an explicit definition sentence \
for a domain-specific technical term (e.g. "X is ...", "X: definition"). \
Option labels, section headings, and general descriptions do NOT qualify. \
Use an empty list [] if no such definitions exist.
- entities: notable concepts, systems, or proper nouns mentioned.
- question_signatures: 2-3 natural questions a reader would ask that this chunk answers.
- keywords: 3-5 retrieval keywords.

Respond with ONLY a JSON object that matches this exact schema:
{_GENERIC_CHUNK_SCHEMA}

Rules:
- file_hash and distilled_at will be filled in by the caller — set them to empty strings "".
- No markdown fences, no extra commentary — just the JSON object."""


def distill_generic_user_prompt(file_name: str, content: str) -> str:
    return f"""\
File: {file_name}

--- Content ---
{content}

Produce the distill JSON for this file."""
